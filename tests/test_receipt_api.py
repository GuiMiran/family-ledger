"""Independent acceptance and failure challenges for receipt command boundaries.

SQLite verifies transaction and persistence behavior here, not PostgreSQL
concurrency. All identities and purchases in this module are synthetic.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import importlib
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.auth import AUDIENCE, ISSUER, issue_family_token
from app.infrastructure.db.orm import (
    Family, InventoryEntry, NormalizationReview, Receipt, ReceiptEvent,
    ReceiptLine, ReceiptSubmission, Supermarket,
)
from app.main import create_app

SECRET = "synthetic-test-secret-with-at-least-32-characters"
PREFIX = "/api/v1"


def purchase():
    return {
        "supermarket_key": "synthetic", "purchase_date": "2026-11-07",
        "total_amount": "6.00", "total_vat": "0.00", "pending_fields": [],
        "overall_confidence": 1,
        "lines": [
            {"line_number": 1, "raw_text": "two apples 4.00", "description": "Synthetic apples",
             "quantity": "2", "unit": "unit", "unit_price": "2.00", "line_total": "4.00", "confidence": 1},
            {"line_number": 2, "raw_text": "one pear 2.00", "description": "Synthetic pear",
             "quantity": "1", "unit": "unit", "unit_price": "2.00", "line_total": "2.00", "confidence": 1},
        ],
    }


def provision(api):
    with api.state.sessions.begin() as session:
        a, b = Family(name="Synthetic A"), Family(name="Synthetic B")
        session.add_all([a, b, Supermarket(name="Synthetic shop", parser_key="synthetic")])
        session.flush()
        return a.id, b.id


def headers(family, key="create-1"):
    return {"Authorization": "Bearer " + issue_family_token(SECRET, family),
            "Idempotency-Key": key}


@pytest.fixture
def api():
    app = create_app("sqlite://", SECRET, initialize_schema=True)
    a, b = provision(app)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield app, client, a, b
    app.state.engine.dispose()


def counts(app):
    models = (Receipt, ReceiptLine, ReceiptEvent, InventoryEntry, ReceiptSubmission)
    with app.state.sessions() as session:
        return tuple(session.scalar(select(func.count()).select_from(model)) for model in models)


@pytest.mark.parametrize("endpoint", ["receipts", "inventory", "analytics"])
def test_private_queries_require_bearer(api, endpoint):
    _, client, _, _ = api
    assert client.get(f"{PREFIX}/{endpoint}").status_code == 401
    assert client.get(f"{PREFIX}/{endpoint}", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    assert client.get(f"{PREFIX}/{endpoint}", headers={"Authorization": "Basic ignored"}).status_code == 401


def test_invalid_expired_and_mismatched_tokens_cannot_write(api):
    app, client, a, b = api
    assert client.post(f"{PREFIX}/receipts", json=purchase(),
                       headers={"Idempotency-Key": "missing-auth"}).status_code == 401
    now = datetime.now(timezone.utc)
    claims = {"sub": str(a), "family_id": str(a), "iss": ISSUER, "aud": AUDIENCE,
              "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)}
    expired = jwt.encode(claims, SECRET, algorithm="HS256")
    claims.update(iat=now, exp=now + timedelta(hours=1), sub=str(b))
    mismatched = jwt.encode(claims, SECRET, algorithm="HS256")
    forged = issue_family_token("another-secret-with-more-than-32-characters", a)
    for token in (expired, mismatched, forged):
        response = client.post(f"{PREFIX}/receipts", json=purchase(),
                               headers={"Authorization": "Bearer " + token, "Idempotency-Key": "unauthorized"})
        assert response.status_code == 401
    assert counts(app) == (0, 0, 0, 0, 0)


def test_configuration_and_provisioning_fail_closed(api):
    _, _, a, _ = api
    for secret in ("", "short"):
        app = create_app("sqlite://", secret, initialize_schema=True)
        with TestClient(app) as client:
            assert client.get(f"{PREFIX}/receipts", headers=headers(a)).status_code == 503
        app.state.engine.dispose()
    app, client, _, _ = api
    absent_family = uuid.uuid4()
    assert client.get(f"{PREFIX}/receipts", headers=headers(absent_family)).status_code == 403
    assert client.post(f"{PREFIX}/receipts", headers=headers(absent_family), json=purchase()).status_code == 403
    assert counts(app) == (0, 0, 0, 0, 0)


def test_same_key_retries_once_and_conflicting_body_rejected(api):
    app, client, a, _ = api
    body = purchase()
    created = client.post(f"{PREFIX}/receipts", headers=headers(a), json=body)
    assert created.status_code == 201, created.text
    again = client.post(f"{PREFIX}/receipts", headers=headers(a), json=body)
    assert again.status_code == 201
    assert again.json() == created.json()
    assert counts(app) == (1, 2, 1, 2, 1)
    changed = deepcopy(body)
    changed["lines"][0]["description"] = "Different valid purchase"
    conflict = client.post(f"{PREFIX}/receipts", headers=headers(a), json=changed)
    assert conflict.status_code == 409
    assert counts(app) == (1, 2, 1, 2, 1)
    with app.state.sessions() as session:
        assert session.scalar(select(ReceiptEvent.processed)) is True


def test_family_scope_comes_from_token_not_body_and_keys_are_per_family(api):
    app, client, a, b = api
    body = purchase()
    body["family_id"] = str(b)
    first = client.post(f"{PREFIX}/receipts", headers=headers(a, "same-key"), json=body)
    assert first.status_code == 201, first.text
    receipt_id = first.json()["id"]
    assert client.get(f"{PREFIX}/receipts/{receipt_id}", headers=headers(b)).status_code == 404
    assert client.post(f"{PREFIX}/receipts/{receipt_id}/confirm", headers=headers(b, "cross-confirm"), json=purchase()).status_code == 404
    assert client.get(f"{PREFIX}/receipts", headers=headers(b)).json() == []
    assert client.get(f"{PREFIX}/inventory", headers=headers(b)).json()["items"] == []
    assert Decimal(client.get(f"{PREFIX}/analytics", headers=headers(b)).json()["confirmed_total"]) == 0
    own = client.post(f"{PREFIX}/receipts", headers=headers(b, "same-key"), json=purchase())
    assert own.status_code == 201 and own.json()["id"] != receipt_id
    assert counts(app) == (2, 4, 2, 4, 2)
    assert len(client.get(f"{PREFIX}/receipts", headers=headers(a)).json()) == 1
    assert len(client.get(f"{PREFIX}/inventory", headers=headers(a)).json()["items"]) == 2


@pytest.mark.parametrize("mutation", ["total", "negative", "quantity", "duplicate-line", "empty"])
def test_client_confidence_cannot_bypass_validation(api, mutation):
    app, client, a, _ = api
    body = purchase()
    if mutation == "total":
        body["total_amount"] = "99.00"
    elif mutation == "negative":
        body["lines"][0]["line_total"] = "-4.00"
    elif mutation == "quantity":
        body["lines"][0]["quantity"] = "0"
    elif mutation == "duplicate-line":
        body["lines"][1]["line_number"] = 1
    else:
        body["lines"] = []
    response = client.post(f"{PREFIX}/receipts", headers=headers(a), json=body)
    assert response.status_code == 422, response.text
    assert counts(app) == (0, 0, 0, 0, 0)


def test_idempotency_key_required(api):
    app, client, a, _ = api
    auth = headers(a)
    del auth["Idempotency-Key"]
    assert client.post(f"{PREFIX}/receipts", headers=auth, json=purchase()).status_code == 422
    assert counts(app) == (0, 0, 0, 0, 0)


def test_undated_pending_has_no_stock_then_confirmation_projects_once(api):
    app, client, a, _ = api
    body = purchase()
    body["purchase_date"] = None
    # Client omits pending_fields intentionally: the server must restore it.
    created = client.post(f"{PREFIX}/receipts", headers=headers(a, "pending"), json=body)
    assert created.status_code == 201, created.text
    receipt_id = created.json()["id"]
    assert created.json()["status"] == "pending_review" and created.json()["purchase_date"] is None
    assert counts(app) == (1, 2, 0, 0, 1)
    analytics = client.get(f"{PREFIX}/analytics", headers=headers(a)).json()
    assert analytics["pending_count"] == 1 and analytics["confirmed_count"] == 0
    period = client.get(f"{PREFIX}/analytics?start=2026-11-01&end=2026-11-30", headers=headers(a)).json()
    assert period["pending_count"] == 0 and period["period_excludes_undated"] is True
    unresolved = client.post(f"{PREFIX}/receipts/{receipt_id}/confirm", headers=headers(a, "confirm"), json=body)
    assert unresolved.status_code == 422
    corrected = purchase()
    corrected["lines"][0]["description"] = "Corrected synthetic apples"
    confirmed = client.post(f"{PREFIX}/receipts/{receipt_id}/confirm", headers=headers(a, "confirm"), json=corrected)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["id"] == receipt_id and confirmed.json()["status"] == "confirmed"
    again = client.post(f"{PREFIX}/receipts/{receipt_id}/confirm", headers=headers(a, "confirm"), json=corrected)
    assert again.status_code == 200 and again.json() == confirmed.json()
    assert counts(app) == (1, 2, 1, 2, 2)
    inventory = client.get(f"{PREFIX}/inventory", headers=headers(a)).json()["items"]
    assert {x["description"] for x in inventory} == {"Corrected synthetic apples", "Synthetic pear"}
    assert client.post(f"{PREFIX}/receipts/{receipt_id}/confirm", headers=headers(a, "different-confirm"), json=corrected).status_code == 409


def test_projection_exception_rolls_back_all_writes(api, monkeypatch):
    app, client, a, _ = api
    module = importlib.import_module("app.main")
    original = module.project_confirmed

    def fail_after_projection(session, receipt):
        original(session, receipt)
        raise RuntimeError("Synthetic failure after projection flush")

    monkeypatch.setattr(module, "project_confirmed", fail_after_projection)
    assert client.post(f"{PREFIX}/receipts", headers=headers(a), json=purchase()).status_code == 500
    assert counts(app) == (0, 0, 0, 0, 0)
    with app.state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(NormalizationReview)) == 0
    monkeypatch.setattr(module, "project_confirmed", original)
    assert client.post(f"{PREFIX}/receipts", headers=headers(a), json=purchase()).status_code == 201
    assert counts(app) == (1, 2, 1, 2, 1)


def test_database_flush_failure_rolls_back_and_returns_unavailable(api, monkeypatch):
    app, client, a, _ = api
    original = Session.flush

    def fail_inventory_flush(session, objects=None):
        if any(isinstance(row, InventoryEntry) for row in session.new):
            raise OperationalError("synthetic projection write", {}, Exception("injected unavailable"))
        return original(session, objects)

    with monkeypatch.context() as patch:
        patch.setattr(Session, "flush", fail_inventory_flush)
        response = client.post(f"{PREFIX}/receipts", headers=headers(a), json=purchase())
        assert response.status_code == 503, response.text
    assert counts(app) == (0, 0, 0, 0, 0)
    assert client.post(f"{PREFIX}/receipts", headers=headers(a), json=purchase()).status_code == 201


def test_confirmation_failure_restores_original_pending_lines(api, monkeypatch):
    app, client, a, _ = api
    pending = purchase()
    pending["purchase_date"] = None
    initial = client.post(f"{PREFIX}/receipts", headers=headers(a, "pending"), json=pending)
    receipt_id = initial.json()["id"]
    corrected = purchase()
    corrected["lines"][0]["description"] = "Replacement that must roll back"
    module = importlib.import_module("app.main")
    original = module.project_confirmed

    def fail_confirmation(session, receipt):
        original(session, receipt)
        raise RuntimeError("Synthetic confirmation failure after replacement")

    with monkeypatch.context() as patch:
        patch.setattr(module, "project_confirmed", fail_confirmation)
        response = client.post(f"{PREFIX}/receipts/{receipt_id}/confirm",
                               headers=headers(a, "confirm"), json=corrected)
        assert response.status_code == 500
    restored = client.get(f"{PREFIX}/receipts/{receipt_id}", headers=headers(a)).json()
    assert restored == initial.json()
    assert counts(app) == (1, 2, 0, 0, 1)
    retry = client.post(f"{PREFIX}/receipts/{receipt_id}/confirm",
                        headers=headers(a, "confirm"), json=corrected)
    assert retry.status_code == 200 and retry.json()["status"] == "confirmed"
    assert counts(app) == (1, 2, 1, 2, 2)


def test_file_database_survives_application_recreation(tmp_path):
    url = f"sqlite:///{tmp_path / 'persistent.sqlite'}"
    first = create_app(url, SECRET, initialize_schema=True)
    a, _ = provision(first)
    with TestClient(first) as client:
        response = client.post(f"{PREFIX}/receipts", headers=headers(a, "persistent"), json=purchase())
        assert response.status_code == 201, response.text
        receipt_id = response.json()["id"]
    first.state.engine.dispose()
    second = create_app(url, SECRET)
    with TestClient(second) as client:
        restored = client.get(f"{PREFIX}/receipts/{receipt_id}", headers=headers(a))
        assert restored.status_code == 200 and restored.json()["id"] == receipt_id
        repeat = client.post(f"{PREFIX}/receipts", headers=headers(a, "persistent"), json=purchase())
        assert repeat.status_code == 201 and repeat.json()["id"] == receipt_id
        assert counts(second) == (1, 2, 1, 2, 1)
        assert len(client.get(f"{PREFIX}/inventory", headers=headers(a)).json()["items"]) == 2
    second.state.engine.dispose()
