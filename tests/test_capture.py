"""Synthetic in-memory images and local process mocks; no private receipt images."""
from io import BytesIO
from pathlib import Path
import subprocess
import uuid

from fastapi.testclient import TestClient
from PIL import Image
import pytest
from sqlalchemy import func, select

from app.core.auth import issue_family_token
from app.domain.ocr import OCRResult, OCRTimeout, OCRUnavailable, OCRUnreadable
from app.infrastructure.db.orm import Family, Receipt, ReceiptLine, ReceiptEvent, InventoryEntry
from app.infrastructure.ocr import MAX_IMAGE_BYTES, MAX_OCR_BYTES, TesseractOCR
from app.main import create_app

SECRET = "synthetic-capture-secret-at-least-32-characters"
TEXT = """SYNTHETIC TEST DATA
LIDL
ALFA CATALITIC 2,25x 2 4,50 B
TOTAL 4,50
02/01/2030 12:34
"""


def image_bytes(format="JPEG", size=(300, 500)):
    buffer = BytesIO()
    Image.new("RGB", size, "white").save(buffer, format=format)
    return buffer.getvalue()


class FakeOCR:
    def __init__(self, result=None, error=None):
        self.result = result or OCRResult(TEXT, provider="synthetic-test")
        self.error = error
        self.calls = 0

    def extract(self, image):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def app_client():
    fake = FakeOCR()
    api = create_app("sqlite://", SECRET, initialize_schema=True, ocr_provider=fake)
    with api.state.sessions.begin() as session:
        family = Family(name="Synthetic Capture Family")
        session.add(family)
        session.flush()
        family_id = family.id
    with TestClient(api, raise_server_exceptions=False) as client:
        yield api, client, fake, {"Authorization": "Bearer " + issue_family_token(SECRET, family_id)}
    api.state.engine.dispose()


def upload(client, headers=None, data=None, mime="image/jpeg", filename="synthetic.jpg"):
    return client.post("/api/v1/receipts/extract", headers=headers or {},
                       files={"image": (filename, data if data is not None else image_bytes(), mime)})


def test_auth_and_provisioning_before_ocr(app_client):
    _, client, fake, _ = app_client
    assert upload(client).status_code == 401
    absent = {"Authorization": "Bearer " + issue_family_token(SECRET, uuid.uuid4())}
    assert upload(client, absent).status_code == 403
    assert fake.calls == 0


@pytest.mark.parametrize("format", ["JPEG", "PNG", "WEBP"])
def test_real_image_bytes_return_draft_without_database_side_effects(app_client, format):
    api, client, fake, headers = app_client
    response = upload(client, headers, image_bytes(format), mime="application/octet-stream", filename="wrong.heic")
    assert response.status_code == 200, response.text  # Neither filename nor MIME is trusted.
    result = response.json()
    assert result["parsed_receipt"]["total_amount"] == "4.50"
    assert result["parsed_receipt"]["purchase_date"] == "2030-01-02"
    assert result["ocr"] == {"provider": "synthetic-test", "confidence": None}
    assert fake.calls == 1
    with api.state.sessions() as session:
        for model in (Receipt, ReceiptLine, ReceiptEvent, InventoryEntry):
            assert session.scalar(select(func.count()).select_from(model)) == 0


def test_missing_date_remains_pending(app_client):
    api, client, fake, headers = app_client
    fake.result = OCRResult(TEXT.replace("02/01/2030 12:34", ""))
    response = upload(client, headers)
    assert response.status_code == 200
    assert response.json()["parsed_receipt"]["purchase_date"] is None
    assert any(p["field_path"] == "purchase_date" for p in response.json()["parsed_receipt"]["pending_fields"])
    assert response.json()["warnings"]


@pytest.mark.parametrize("data", [b"not image", b"\x00\x00\x00\x18ftypheicinvalid", b"\xff\xd8\xfftruncated"])
def test_mime_spoof_and_unsupported_formats_are_rejected(app_client, data):
    _, client, fake, headers = app_client
    response = upload(client, headers, data)
    assert response.status_code == 415
    assert "HEIC" in response.json()["detail"]
    assert fake.calls == 0


def test_oversize_bytes_rejected_before_ocr(app_client):
    _, client, fake, headers = app_client
    response = upload(client, headers, b"\xff\xd8\xff" + b"x" * MAX_IMAGE_BYTES)
    assert response.status_code == 413
    assert fake.calls == 0


def test_pixel_bomb_rejected_without_decoding(app_client, monkeypatch):
    from app.infrastructure import ocr
    _, client, fake, headers = app_client
    # Lower the bound, exercising actual PNG dimension parsing with a small fixture.
    monkeypatch.setattr(ocr, "MAX_PIXELS", 10000)
    response = upload(client, headers, image_bytes("PNG"))
    assert response.status_code == 413
    assert fake.calls == 0


def test_tiny_image_requires_recapture(app_client):
    _, client, fake, headers = app_client
    assert upload(client, headers, image_bytes(size=(20, 20))).status_code == 415
    assert fake.calls == 0


@pytest.mark.parametrize("error,status", [(OCRTimeout("private/tmp/path"), 504), (OCRUnavailable("sensitive internal executable"), 503), (OCRUnreadable("private OCR text"), 422)])
def test_provider_failures_are_sanitized(app_client, error, status):
    _, client, fake, headers = app_client
    fake.error = error
    response = upload(client, headers)
    assert response.status_code == status
    assert str(error) not in response.text


@pytest.mark.parametrize("text", ["unrecognizable text", "LIDL\nTOTAL 8,00", "LIDL\nALFA 2,00 B\nTOTAL 9,00"])
def test_no_usable_or_reconciled_lines_asks_for_recapture(app_client, text):
    _, client, fake, headers = app_client
    fake.result = OCRResult(text)
    response = upload(client, headers)
    assert response.status_code == 422
    assert "foto" in response.json()["detail"]


def test_excess_files_rejected(app_client):
    _, client, fake, headers = app_client
    response = client.post("/api/v1/receipts/extract", headers=headers,
        files=[("image", ("a.jpg", image_bytes())), ("image", ("b.jpg", image_bytes()))])
    assert response.status_code == 400
    assert fake.calls == 0


class FakeProcess:
    def __init__(self, command, *, output=b"synthetic OCR", timeout=False):
        self.stdout = BytesIO(output)
        self.command = command
        self.returncode = None
        self.timeout = timeout
        self.killed = False

    def wait(self, timeout=None):
        if self.timeout and not self.killed:
            raise subprocess.TimeoutExpired(self.command, timeout)
        self.returncode = -9 if self.killed else 0
        return self.returncode

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True


def test_tesseract_command_and_temporary_cleanup(monkeypatch):
    seen = []
    def popen(command, **kwargs):
        assert command[0] == "tesseract"
        assert command[2:] == ["stdout", "-l", "spa+cat+eng", "--psm", "6"]
        assert kwargs["shell"] is False
        assert kwargs["stderr"] == subprocess.DEVNULL
        path = Path(command[1])
        assert path.exists()
        seen.append(path)
        return FakeProcess(command)
    monkeypatch.setattr("app.infrastructure.ocr.subprocess.Popen", popen)
    assert TesseractOCR().extract(image_bytes()).text == "synthetic OCR"
    assert all(not path.exists() and not path.parent.exists() for path in seen)


@pytest.mark.parametrize("mode,error", [("timeout", OCRTimeout), ("missing", OCRUnavailable), ("large", OCRUnreadable)])
def test_adapter_timeout_binary_missing_and_bounded_output_cleanup(monkeypatch, mode, error):
    seen = []
    processes = []
    def popen(command, **kwargs):
        seen.append(Path(command[1]))
        if mode == "missing":
            raise FileNotFoundError("private path must never reach API")
        process = FakeProcess(command, output=b"x" * (MAX_OCR_BYTES + 1) if mode == "large" else b"OCR", timeout=mode == "timeout")
        processes.append(process)
        return process
    monkeypatch.setattr("app.infrastructure.ocr.subprocess.Popen", popen)
    with pytest.raises(error):
        TesseractOCR().extract(image_bytes())
    assert all(not path.exists() and not path.parent.exists() for path in seen)
    if mode != "missing":
        assert processes[0].killed


def test_actual_decompression_bomb_header_rejected_before_load(app_client):
    import struct
    import zlib
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    bomb = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 100000, 100000, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"")) + chunk(b"IEND", b"")
    _, client, fake, headers = app_client
    assert upload(client, headers, bomb, mime="image/png").status_code == 413
    assert fake.calls == 0


def test_chunked_request_cannot_bypass_wire_limit(app_client):
    from app.api.capture import WIRE_LIMIT
    _, client, fake, headers = app_client
    def body():
        yield b'--synthetic\r\nContent-Disposition: form-data; name="image"; filename="test.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'
        for _ in range(WIRE_LIMIT // 65536 + 2):
            yield b"x" * 65536
        yield b"\r\n--synthetic--\r\n"
    response = client.post("/api/v1/receipts/extract", content=body(),
        headers={**headers, "Content-Type": "multipart/form-data; boundary=synthetic"})
    assert response.status_code == 413
    assert fake.calls == 0


def test_makro_missing_vat_and_date_are_pending_draft(app_client):
    _, client, fake, headers = app_client
    fake.result = OCRResult("MAKRO\n00002001 SYNTHETIC ITEM UD 3,000 1 3,00 1 3,00 1\nTotal a pagar 3,00")
    response = upload(client, headers)
    assert response.status_code == 200
    pending = {field["field_path"] for field in response.json()["parsed_receipt"]["pending_fields"]}
    assert {"purchase_date", "total_vat"} <= pending


def test_busy_ocr_is_nonblocking_without_writes_and_failure_releases_permit(app_client):
    api, client, fake, headers = app_client
    assert api.state.ocr_capacity.acquire(blocking=False)
    try:
        response = upload(client, headers)
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "5"
        assert fake.calls == 0
        with api.state.sessions() as session:
            for model in (Receipt, ReceiptLine, ReceiptEvent, InventoryEntry):
                assert session.scalar(select(func.count()).select_from(model)) == 0
    finally:
        api.state.ocr_capacity.release()
    fake.error = OCRTimeout()
    assert upload(client, headers).status_code == 504
    fake.error = None
    assert upload(client, headers).status_code == 200
    assert upload(client, headers, b"not image").status_code == 415
    assert upload(client, headers).status_code == 200


def test_exif_orientation_is_applied_and_metadata_stripped_before_tesseract(monkeypatch):
    buffer = BytesIO()
    source = Image.new("RGB", (300, 500), "white")
    exif = Image.Exif()
    exif[274] = 6  # Rotate 90 degrees clockwise.
    exif[315] = "SYNTHETIC PRIVATE TEST METADATA"
    source.save(buffer, format="JPEG", exif=exif)
    source.close()
    seen = []
    def popen(command, **kwargs):
        path = Path(command[1])
        seen.append(path)
        assert path.name == "input.png"
        with Image.open(path) as normalized:
            assert normalized.size == (500, 300)
            assert normalized.mode == "RGB"
            assert normalized.format == "PNG"
            assert not normalized.getexif()
            assert not normalized.info
        assert b"SYNTHETIC PRIVATE TEST METADATA" not in path.read_bytes()
        return FakeProcess(command)
    monkeypatch.setattr("app.infrastructure.ocr.subprocess.Popen", popen)
    assert TesseractOCR().extract(buffer.getvalue()).text == "synthetic OCR"
    assert all(not path.parent.exists() for path in seen)
