"""Real PostgreSQL qualification on an explicitly disposable CI database."""
import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.core.auth import issue_family_token
from app.main import create_app
from app.infrastructure.db.orm import Base, Family, Receipt, ReceiptLine, ReceiptSubmission, ReceiptEvent, InventoryEntry
from app.infrastructure.db.session import create_db_engine
from app.infrastructure.db.migrations import migrate_database

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="Explicit disposable PostgreSQL TEST_DATABASE_URL required")
SECRET = "synthetic-postgres-test-secret-32-characters"

@pytest.fixture
def pg_app():
    engine = create_db_engine(URL)
    if engine.dialect.name != "postgresql" or not engine.url.database.endswith("_test"):
        pytest.fail("PostgreSQL qualification requires a disposable database name ending in _test")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    app = create_app(URL, SECRET)
    with app.state.sessions.begin() as session:
        family = Family(name="Synthetic PostgreSQL family")
        session.add(family)
        session.flush()
        family_id = family.id
    yield app, family_id
    app.state.engine.dispose()
    Base.metadata.drop_all(engine)
    engine.dispose()

def payload(pending=False):
    return {"supermarket_key": "generic", "purchase_date": None if pending else "2026-11-07",
            "total_amount": "10.00", "total_vat": "0.00", "pending_fields": [],
            "lines": [{"line_number": 1, "raw_text": "SYNTHETIC", "description": "SYNTHETIC",
                       "quantity": "1", "unit": "unit", "line_total": "10.00", "unit_price": "10.00"}]}

def test_postgres_concurrent_create_retry_is_atomic(pg_app):
    app, family_id = pg_app
    headers = {"Authorization": "Bearer " + issue_family_token(SECRET, family_id), "Idempotency-Key": "same-create"}
    def submit(_):
        with TestClient(app) as client:
            response = client.post("/api/v1/receipts", json=payload(), headers=headers)
            assert response.status_code == 201, response.text
            return response.json()["id"]
    with ThreadPoolExecutor(max_workers=4) as workers:
        ids = list(workers.map(submit, range(4)))
    assert len(set(ids)) == 1
    with app.state.sessions() as session:
        for model in (Receipt, ReceiptLine, ReceiptSubmission, ReceiptEvent, InventoryEntry):
            assert session.scalar(select(func.count()).select_from(model)) == 1
    restarted = create_app(URL, SECRET)
    with TestClient(restarted) as client:
        assert client.get("/api/v1/receipts/" + ids[0], headers=headers).status_code == 200
    restarted.state.engine.dispose()

def test_postgres_concurrent_pending_confirmation_once(pg_app):
    app, family_id = pg_app
    auth = {"Authorization": "Bearer " + issue_family_token(SECRET, family_id)}
    with TestClient(app) as client:
        response = client.post("/api/v1/receipts", json=payload(True), headers={**auth, "Idempotency-Key": "pending"})
        assert response.status_code == 201, response.text
        receipt_id = response.json()["id"]
    def confirm(_):
        with TestClient(app) as client:
            response = client.post(f"/api/v1/receipts/{receipt_id}/confirm", json=payload(),
                                   headers={**auth, "Idempotency-Key": "same-confirm"})
            assert response.status_code == 200, response.text
            return response.json()
    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(confirm, range(4)))
    assert all(row["id"] == receipt_id and row["status"] == "confirmed" for row in results)
    with app.state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(Receipt)) == 1
        assert session.scalar(select(func.count()).select_from(ReceiptLine)) == 1
        assert session.scalar(select(func.count()).select_from(ReceiptEvent)) == 1
        assert session.scalar(select(func.count()).select_from(InventoryEntry)) == 1
        assert session.scalar(select(func.count()).select_from(ReceiptSubmission)) == 2


def test_postgres_explicit_legacy_alias_migration_retains_rows(pg_app):
    from app.infrastructure.db.orm import Product, ProductAlias, Supermarket
    app, family_id = pg_app
    with app.state.sessions.begin() as session:
        shop = Supermarket(name='Synthetic migration market', parser_key='makro')
        private = Product(family_id=family_id, canonical_name='Synthetic private')
        shared = Product(canonical_name='Synthetic shared')
        session.add_all([shop,private,shared]); session.flush()
        a = ProductAlias(product_id=private.id,supermarket_id=shop.id,alias_text='PRIVATE LEGACY',match_type='manual')
        b = ProductAlias(product_id=shared.id,supermarket_id=shop.id,alias_text='UNKNOWN LEGACY',match_type='manual')
        session.add_all([a,b]);session.flush();private_id=a.id;unknown_id=b.id
    with app.state.engine.begin() as connection:
        connection.exec_driver_sql('ALTER TABLE product_aliases DROP CONSTRAINT uq_alias_scoped')
        connection.exec_driver_sql('ALTER TABLE product_aliases DROP COLUMN family_id')
        connection.exec_driver_sql('ALTER TABLE product_aliases ADD CONSTRAINT uq_alias_per_market UNIQUE (supermarket_id,alias_text)')
    result = migrate_database(app.state.engine)
    assert result['status'] == 'migrated'
    with app.state.sessions() as session:
        assert session.get(ProductAlias,private_id).family_id == family_id
        quarantined = session.get(ProductAlias,unknown_id).family_id
        assert quarantined is not None and quarantined != family_id
        assert session.scalar(select(func.count()).select_from(ProductAlias)) == 2
    assert migrate_database(app.state.engine)['status'] == 'current'


def test_postgres_shopping_refresh_serializes_family_snapshot(pg_app):
    from datetime import datetime,timezone
    from app.domain.shopping import PriceOffer
    from app.infrastructure.prices import CollectionResult
    from app.infrastructure.db.orm import PriceObservationRow,ShoppingAuditRow,ShoppingProfileRow
    app,family_id=pg_app
    class Source:
        def collect(self,profile):
            offer=PriceOffer(id='synthetic-pg',store='mercadona',product_name='Synthetic whole milk',
                comparison_group='milk_whole_uht',pack_quantity='1',pack_unit='l',price='1',
                source_name='synthetic-pg',source_url='https://mercadona.es/product/synthetic',
                observed_at=datetime.now(timezone.utc),postal_code=profile.postal_code,location_verified=True)
            return CollectionResult([offer],[{'store':'mercadona','status':'observations_received'}])
    app.state.shopping_collector=Source()
    headers={'Authorization':'Bearer '+issue_family_token(SECRET,family_id)}
    from tests.shopping_fixtures import configured_profile
    with TestClient(app) as client:
        assert client.put('/api/v1/shopping/profile',headers=headers,json=configured_profile().model_dump(mode='json')).status_code==200
    def refresh(_):
        with TestClient(app) as client:
            response=client.post('/api/v1/shopping/refresh',headers=headers)
            assert response.status_code==200,response.text
            return response.json()['comparison']['coverage']
    with ThreadPoolExecutor(max_workers=4) as workers:
        assert list(workers.map(refresh,range(4)))==[1]*4
    with app.state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(PriceObservationRow))==1
        assert session.scalar(select(func.count()).select_from(ShoppingAuditRow))==4
    for table in (PriceObservationRow.__table__,ShoppingAuditRow.__table__,ShoppingProfileRow.__table__):
        table.drop(app.state.engine)
    assert migrate_database(app.state.engine)['status']=='current'
    with app.state.sessions() as session:
        assert session.get(Family,family_id).name=='Synthetic PostgreSQL family'
