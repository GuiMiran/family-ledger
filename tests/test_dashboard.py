"""Family app dashboard reports only confirmed records owned by the JWT family."""
from datetime import date
from decimal import Decimal
import uuid
from fastapi.testclient import TestClient
from app.core.auth import issue_family_token
from app.infrastructure.db.orm import Family,Receipt,Supermarket
from app.main import create_app

SECRET='synthetic-dashboard-secret-longer-than-32-characters'


def test_dashboard_empty_private_and_recorded_only():
    app=create_app('sqlite://',SECRET,initialize_schema=True)
    with app.state.sessions.begin() as session:
        a,b=Family(name='Synthetic A'),Family(name='Synthetic B')
        shop=Supermarket(name='Synthetic shop',parser_key='synthetic')
        session.add_all([a,b,shop]);session.flush();aid,bid=a.id,b.id
        session.add_all([
            Receipt(family_id=aid,supermarket_id=shop.id,purchase_date=date.today(),total_amount=Decimal('12.50'),status='confirmed'),
            Receipt(family_id=aid,purchase_date=None,total_amount=Decimal('99'),status='pending_review'),
            Receipt(family_id=bid,purchase_date=date.today(),total_amount=Decimal('999'),status='confirmed'),
        ])
    def headers(key):return {'Authorization':'Bearer '+issue_family_token(SECRET,key)}
    with TestClient(app) as client:
        assert client.get('/api/v1/dashboard').status_code==401
        result=client.get('/api/v1/dashboard',headers=headers(aid))
        assert result.status_code==200,result.text
        body=result.json()
        assert body['confirmed_total']=='12.50' and body['confirmed_count']==1 and body['pending_count']==1
        assert len(body['monthly'])==6 and sum(x['count'] for x in body['monthly'])==1
        assert sum(Decimal(x['total']) for x in body['monthly'])==Decimal('12.50')
        assert body['by_supermarket']==[{'name':'Synthetic shop','total':'12.50','count':1}]
        assert body['savings'] is None and body['waste'] is None and body['confirmed_discounts'] is None
        assert body['coverage']=='confirmed_stored_receipts_only'
        assert client.get('/api/v1/dashboard',headers=headers(uuid.uuid4())).status_code==403
    app.state.engine.dispose()


def test_empty_dashboard_is_no_observations_not_measured_saving():
    app=create_app('sqlite://',SECRET,initialize_schema=True)
    with app.state.sessions.begin() as session:
        family=Family(name='Synthetic blank');session.add(family);session.flush();fid=family.id
    with TestClient(app) as client:
        r=client.get('/api/v1/dashboard',headers={'Authorization':'Bearer '+issue_family_token(SECRET,fid)})
        assert r.json()['confirmed_count']==0 and r.json()['by_supermarket']==[]
        assert r.json()['savings'] is None and all(x['count']==0 for x in r.json()['monthly'])
    app.state.engine.dispose()
