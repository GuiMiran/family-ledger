"""Synthetic invitation recovery; never real family data or production secrets."""
import hashlib
import time
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import create_app
from app.infrastructure.db.orm import Family, Receipt
from app.core.identity import ALIAS_QUARANTINE_FAMILY_ID

CODE = 'synthetic-test-invitation-secret-1234567890'
SECRET = 'synthetic-test-jwt-secret-12345678901234567890'


def configured(monkeypatch, **overrides):
    family_id = uuid.uuid4()
    values = {'FAMILY_INVITE_SHA256': hashlib.sha256(CODE.encode()).hexdigest(),
              'FAMILY_INVITE_EXPIRES_AT': str(time.time()+3600),
              'FAMILY_BOOTSTRAP_ID': str(family_id)}
    values.update(overrides)
    for key, value in values.items():monkeypatch.setenv(key, value)
    api = create_app('sqlite:///:memory:', SECRET, initialize_schema=True)
    with api.state.sessions.begin() as session:session.add(Family(id=family_id, name='Synthetic family'))
    return api, TestClient(api), family_id


def test_valid_invite_existing_family_and_no_writes(monkeypatch):
    api, client, family_id = configured(monkeypatch)
    other_id=uuid.uuid4()
    with api.state.sessions.begin() as session:session.add(Family(id=other_id,name='Other synthetic family'))
    r=client.post('/api/v1/access/exchange',json={'invitation':CODE})
    assert r.status_code==200 and r.headers['cache-control']=='no-store'
    token=r.json()['access_token']
    assert r.json()['expires_in']==28800 and r.json()['token_type']=='bearer'
    headers={'Authorization':'Bearer '+token}
    assert client.get('/api/v1/shopping/profile',headers=headers).json()['family_name']=='Synthetic family'
    assert client.get('/api/v1/receipts',headers=headers).json()==[]
    with api.state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(Family))==2
        assert session.scalar(select(func.count()).select_from(Receipt))==0
    assert CODE not in r.text and str(other_id) not in r.text


@pytest.mark.parametrize('overrides',[
    {'FAMILY_INVITE_SHA256':''}, {'FAMILY_INVITE_SHA256':'bad'},
    {'FAMILY_INVITE_EXPIRES_AT':'NaN'}, {'FAMILY_INVITE_EXPIRES_AT':'inf'},
    {'FAMILY_INVITE_EXPIRES_AT':'not-a-date'}, {'FAMILY_BOOTSTRAP_ID':'bad'},
    {'FAMILY_BOOTSTRAP_ID':str(ALIAS_QUARANTINE_FAMILY_ID)},
])
def test_invalid_config_fails_closed(monkeypatch,overrides):
    _, client, _=configured(monkeypatch,**overrides)
    r=client.post('/api/v1/access/exchange',json={'invitation':CODE})
    assert r.status_code==503 and CODE not in r.text


def test_wrong_and_expired_invites_same_rejection(monkeypatch):
    _,client,_=configured(monkeypatch)
    wrong=client.post('/api/v1/access/exchange',json={'invitation':'z'*40})
    _,expired,_=configured(monkeypatch,FAMILY_INVITE_EXPIRES_AT=str(time.time()-1))
    old=expired.post('/api/v1/access/exchange',json={'invitation':CODE})
    assert wrong.status_code==old.status_code==401
    assert wrong.json()==old.json()


def test_unprovisioned_invite_rejected_without_creation(monkeypatch):
    api,client,family_id=configured(monkeypatch)
    with api.state.sessions.begin() as session:session.delete(session.get(Family,family_id))
    assert client.post('/api/v1/access/exchange',json={'invitation':CODE}).status_code==401
    with api.state.sessions() as session:assert session.scalar(select(func.count()).select_from(Family))==0


def test_client_cannot_select_family(monkeypatch):
    _,client,_=configured(monkeypatch)
    assert client.post('/api/v1/access/exchange',json={'invitation':CODE,'family_id':str(uuid.uuid4())}).status_code==422


def test_failed_attempts_bounded_and_throttled(monkeypatch):
    _,client,_=configured(monkeypatch)
    for _ in range(20):assert client.post('/api/v1/access/exchange',json={'invitation':'x'*40}).status_code==401
    r=client.post('/api/v1/access/exchange',json={'invitation':CODE})
    assert r.status_code==429 and r.headers['retry-after']=='60'
