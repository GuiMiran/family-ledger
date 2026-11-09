"""Explicit 0.2 -> shopping tables preserves existing identity and data."""
from sqlalchemy import inspect,select
from app.infrastructure.db.orm import Base,Family,ShoppingProfileRow,PriceObservationRow,ShoppingAuditRow
from app.infrastructure.db.session import create_db_engine,create_session_factory
from app.infrastructure.db.migrations import migrate_database


def test_upgrade_from_v020_adds_shopping_tables_without_replacing_family():
    engine=create_db_engine('sqlite://')
    new={'shopping_profiles','price_observations','shopping_audits'}
    Base.metadata.create_all(engine,tables=[table for name,table in Base.metadata.tables.items() if name not in new])
    factory=create_session_factory(engine)
    with factory.begin() as session:
        family=Family(name='Synthetic retained family');session.add(family);session.flush();key=family.id
    assert not new.intersection(inspect(engine).get_table_names())
    assert migrate_database(engine)['status']=='current'
    assert new.issubset(inspect(engine).get_table_names())
    with factory() as session:
        assert session.get(Family,key).name=='Synthetic retained family'
    assert migrate_database(engine)['status']=='current'
    engine.dispose()
