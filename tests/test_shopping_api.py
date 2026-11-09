"""Synthetic source-backed API challenges. No retailer request is made here."""
from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.core.auth import issue_family_token
from app.domain.shopping import PriceOffer, ShoppingProfile
from app.infrastructure.prices import CollectionResult
from app.infrastructure.db.orm import Family, Receipt, InventoryEntry, ShoppingAuditRow
from app.main import create_app

SECRET = 'synthetic-shopping-secret-more-than-32-characters'

class Source:
    def __init__(self):
        self.calls = 0
    def collect(self, profile):
        self.calls += 1
        offer = PriceOffer(id='milk', store='mercadona', product_name='Synthetic whole milk',
            comparison_group='milk_whole_uht', pack_quantity='1', pack_unit='l', price='1.10',
            source_url='https://tienda.mercadona.es/product/123', source_name='synthetic',
            observed_at=datetime.now(timezone.utc), postal_code=profile.postal_code, location_verified=True)
        return CollectionResult([offer], [{'store': 'mercadona', 'status': 'observations_received'}])

@pytest.fixture
def api():
    source = Source()
    app = create_app('sqlite://', SECRET, initialize_schema=True, shopping_collector=source)
    with app.state.sessions.begin() as session:
        a,b=Family(name='Synthetic A'),Family(name='Synthetic B')
        session.add_all([a,b]); session.flush(); ids=(a.id,b.id)
    with TestClient(app) as client:
        yield app,client,*ids,source
    app.state.engine.dispose()

def auth(family):
    return {'Authorization':'Bearer '+issue_family_token(SECRET,family)}

@pytest.mark.parametrize('path,method',[('profile','get'),('profile','put'),('compare','get'),('refresh','post'),('agent','post')])
def test_auth_required(api,path,method):
    _,client,_,_,source=api
    assert getattr(client,method)('/api/v1/shopping/'+path).status_code==401
    assert source.calls==0

def test_profile_isolated_persisted_and_zone_not_taken_from_other_family(api):
    _,client,a,b,_=api
    profile=client.get('/api/v1/shopping/profile',headers=auth(a)).json()
    assert profile['postal_code']=='08038'
    assert len(profile['basket'])==8
    assert next(x for x in profile['basket'] if x['key']=='eggs')['comparison_group']=='eggs_size_pending'
    profile['postal_code']='08001'; profile['max_budget']='20'; profile['family_id']=str(b)
    assert client.put('/api/v1/shopping/profile',headers=auth(a),json=profile).status_code==200
    assert client.get('/api/v1/shopping/profile',headers=auth(a)).json()['postal_code']=='08001'
    assert client.get('/api/v1/shopping/profile',headers=auth(b)).json()['postal_code']=='08038'
    assert client.get('/api/v1/shopping/profile',headers=auth(uuid.uuid4())).status_code==403

def test_refresh_compare_agent_are_family_scoped_and_do_not_purchase(api):
    app,client,a,b,source=api
    response=client.post('/api/v1/shopping/refresh',headers=auth(a))
    assert response.status_code==200,response.text
    assert response.json()['comparison']['coverage']==1
    assert client.get('/api/v1/shopping/compare',headers=auth(a)).json()['comparison']['coverage']==1
    assert client.get('/api/v1/shopping/compare',headers=auth(b)).json()['comparison']['coverage']==0
    plan=client.post('/api/v1/shopping/agent',headers=auth(a)).json()
    assert plan['agent']['llm_used'] is False
    assert plan['agent']['purchases_executed']==0
    assert plan['agent']['achieved_savings'] is None
    assert plan['agent']['complete'] is False
    assert plan['agent']['within_budget'] is None
    assert plan['agent']['estimated_outlay']=='1.10'
    assert source.calls==2
    with app.state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(Receipt))==0
        assert session.scalar(select(func.count()).select_from(InventoryEntry))==0
        assert session.scalar(select(func.count()).select_from(ShoppingAuditRow).where(ShoppingAuditRow.family_id==b))==0

def test_profile_change_marks_coverage_as_not_refreshed_and_excludes_previous_zone(api):
    _,client,a,_,_=api
    client.post('/api/v1/shopping/refresh',headers=auth(a))
    profile=client.get('/api/v1/shopping/profile',headers=auth(a)).json()
    profile['postal_code']='08001'
    client.put('/api/v1/shopping/profile',headers=auth(a),json=profile)
    result=client.get('/api/v1/shopping/compare',headers=auth(a)).json()
    assert result['comparison']['coverage']==0
    assert all(x['status']=='not_refreshed' for x in result['coverage'])


def test_agent_optimizes_checkout_not_only_unit_price_and_never_subtracts_cashback():
    from app.application.shopping_agent import advise
    from app.domain.shopping import compare
    profile=ShoppingProfile(basket=[{'key':'milk','label':'milk','comparison_group':'milk_whole_uht','unit':'l','desired_quantity':'1'}],max_budget='2')
    base=dict(store='mercadona',product_name='synthetic',comparison_group='milk_whole_uht',pack_unit='l',source_url='https://mercadona.es/product',source_name='test',observed_at=datetime.now(timezone.utc),postal_code='08038',location_verified=True)
    offers=[PriceOffer(id='bulk',price='5',pack_quantity='6',**base),PriceOffer(id='one',price='1.10',pack_quantity='1',cashback='1',**base)]
    comparison=compare(profile,offers)
    assert comparison['items'][0]['top_offers'][0]['id']=='bulk'
    plan=advise(profile,comparison)
    assert plan['plan'][0]['offer']['id']=='one'
    assert plan['estimated_outlay']=='1.10' and plan['within_budget'] is True
    assert plan['potential_difference']=='3.90'


def test_provider_outage_clears_snapshot_instead_of_relabelling_old_quote(api):
    app,client,a,_,_=api
    client.post('/api/v1/shopping/refresh',headers=auth(a))
    class Outage:
        def collect(self,profile):
            return CollectionResult([], [{'store':'mercadona','status':'source_unavailable'}])
    app.state.shopping_collector=Outage()
    result=client.post('/api/v1/shopping/refresh',headers=auth(a)).json()
    assert result['comparison']['coverage']==0
    assert client.get('/api/v1/shopping/compare',headers=auth(a)).json()['comparison']['coverage']==0
    assert result['coverage'][0]['status']=='source_unavailable'


def test_web_invite_is_expiring_fragment_not_query_and_rejects_insecure_host(tmp_path,monkeypatch,capsys):
    from urllib.parse import urlsplit,parse_qs
    from app.admin import main
    from app.infrastructure.db.session import create_db_engine,create_session_factory
    from app.infrastructure.db.migrations import initialize_database
    import jwt
    url=f'sqlite:///{tmp_path / "invite.db"}'
    monkeypatch.setenv('DATABASE_URL',url);monkeypatch.setenv('JWT_SECRET',SECRET)
    engine=create_db_engine(url);initialize_database(engine)
    with create_session_factory(engine).begin() as session:
        family=Family(name='Synthetic invite');session.add(family);session.flush();key=family.id
    assert main(['token','--family',str(key),'--web-url','https://family.example'])==0
    target=urlsplit(capsys.readouterr().out.strip())
    assert target.query=='' and target.fragment.startswith('token=')
    claims=jwt.decode(parse_qs(target.fragment)['token'][0],SECRET,algorithms=['HS256'],audience='family-ledger',issuer='family-ledger-admin')
    assert claims['family_id']==str(key) and claims['exp']>claims['iat']
    assert main(['token','--family',str(key),'--web-url','http://family.example'])==1
    assert capsys.readouterr().out==''
    engine.dispose()


def test_public_shell_does_not_expose_private_api_and_api_disallows_cache(tmp_path,monkeypatch):
    (tmp_path/'index.html').write_text('<html><title>Family Ledger</title><div id="root"></div></html>')
    monkeypatch.setenv('SHOPPING_WEB_DIR',str(tmp_path))
    app=create_app('sqlite://',SECRET,initialize_schema=True,shopping_collector=Source())
    with TestClient(app) as client:
        assert client.get('/').status_code==200
        response=client.get('/api/v1/shopping/profile')
        assert response.status_code==401
        assert response.headers['cache-control']=='no-store'
        assert client.get('/health').json()=={'status':'ok'}
    app.state.engine.dispose()
