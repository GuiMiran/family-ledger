"""Adversarial input checks preserve numeric values across database storage."""
from copy import deepcopy
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.core.auth import issue_family_token
from app.domain.receipts.models import ParsedReceipt
from app.application.receipt_commands import validated_receipt
from app.infrastructure.db.orm import Family, Receipt
from app.main import create_app


def body():
    return {"supermarket_key":"generic", "purchase_date":"2026-11-07", "total_amount":"6.00", "total_vat":"0.00",
            "lines":[{"line_number":1,"description":"Synthetic","raw_text":"Synthetic","quantity":"1","unit":"unit","line_total":"6.00"}]}


def test_subcent_lines_cannot_confirm_then_round_away():
    payload = body()
    payload['lines'] = [{**payload['lines'][0], 'line_number':i+1, 'line_total':'0.004'} for i in range(100)]
    payload['total_amount'] = '0.40'
    app = create_app('sqlite://', 'synthetic-validation-secret-at-least-32-chars', initialize_schema=True)
    with app.state.sessions.begin() as session:
        family = Family(name='Synthetic')
        session.add(family); session.flush(); family_id = family.id
    token = issue_family_token(app.state.jwt_secret, family_id)
    with TestClient(app) as client:
        result = client.post('/api/v1/receipts', json=payload, headers={'Authorization':'Bearer '+token,'Idempotency-Key':'subcent'})
    assert result.status_code == 422
    with app.state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(Receipt)) == 0


@pytest.mark.parametrize('field,value', [('quantity','0.0001'),('quantity','10000000'),('unit_price','0.00001'),
                                        ('line_total','100000000'),('vat_rate','100'),('line_number',32768)])
def test_line_storage_precision_is_enforced(field,value):
    payload = body(); payload['lines'][0][field] = value
    with pytest.raises(ValueError):
        validated_receipt(ParsedReceipt.model_validate(payload))


@pytest.mark.parametrize('market',['generic','lidl','mercadona','makro'])
def test_vat_cannot_exceed_paid_total(market):
    payload = body(); payload.update(supermarket_key=market,total_vat='9.00')
    with pytest.raises(ValueError, match='VAT cannot exceed'):
        validated_receipt(ParsedReceipt.model_validate(payload))


def test_missing_makro_vat_remains_pending_without_inventing_tax():
    payload = body(); payload.update(supermarket_key='makro',total_vat=None,total_amount='6.60')
    receipt = validated_receipt(ParsedReceipt.model_validate(payload))
    assert any(field.field_path == 'total_vat' for field in receipt.pending_fields)
    assert receipt.total_vat is None


def test_small_reconciliation_difference_is_pending_not_confirmed():
    payload = body(); payload['total_amount'] = '6.04'
    receipt = validated_receipt(ParsedReceipt.model_validate(payload))
    field = next(field for field in receipt.pending_fields if field.field_path == 'total_amount')
    assert field.suggestion == '6.00'


def test_idempotent_response_is_stable_for_integer_amount_input():
    payload = body(); payload['total_amount'] = 6; payload['total_vat'] = 0
    payload['lines'][0]['quantity'] = 1; payload['lines'][0]['line_total'] = 6
    app = create_app('sqlite://', 'synthetic-validation-secret-at-least-32-chars', initialize_schema=True)
    with app.state.sessions.begin() as session:
        family = Family(name='Synthetic stable response')
        session.add(family); session.flush(); family_id = family.id
    headers = {'Authorization':'Bearer '+issue_family_token(app.state.jwt_secret,family_id),'Idempotency-Key':'integer'}
    with TestClient(app) as client:
        first = client.post('/api/v1/receipts',json=payload,headers=headers)
        repeated = client.post('/api/v1/receipts',json=payload,headers=headers)
    assert first.status_code == repeated.status_code == 201
    assert first.json() == repeated.json()


def test_reserved_quarantine_identity_cannot_authenticate_even_with_signed_token():
    import jwt
    from datetime import datetime, timedelta, timezone
    from app.core.identity import ALIAS_QUARANTINE_FAMILY_ID
    from app.core.auth import ISSUER, AUDIENCE
    secret = 'synthetic-validation-secret-at-least-32-chars'
    with pytest.raises(ValueError, match='Reserved'):
        issue_family_token(secret, ALIAS_QUARANTINE_FAMILY_ID)
    now = datetime.now(timezone.utc)
    token = jwt.encode({'sub':str(ALIAS_QUARANTINE_FAMILY_ID),'family_id':str(ALIAS_QUARANTINE_FAMILY_ID),
                        'iss':ISSUER,'aud':AUDIENCE,'iat':now,'exp':now+timedelta(hours=1)},secret,algorithm='HS256')
    with TestClient(create_app(jwt_secret=secret)) as client:
        assert client.get('/api/v1/receipts',headers={'Authorization':'Bearer '+token}).status_code == 401
