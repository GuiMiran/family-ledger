from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FIXTURES = Path(__file__).parent / "fixtures"


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_parse_endpoint_makro():
    text = (FIXTURES / "makro_ticket.txt").read_text(encoding="utf-8")
    r = client.post("/api/v1/receipts/parse", json={"ocr_text": text})
    assert r.status_code == 200
    body = r.json()
    assert body["supermarket_key"] == "makro"
    assert body["total_amount"] == "211.87"
    assert len(body["lines"]) == 17


def test_parse_endpoint_unknown_ticket():
    r = client.post("/api/v1/receipts/parse", json={"ocr_text": "texto cualquiera"})
    assert r.status_code == 200
    body = r.json()
    assert body["supermarket_key"] == "unknown"
    assert body["pending_fields"][0]["field_path"] == "supermarket_id"
