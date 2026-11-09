# @spectra US-001
# @spectra US-003
# @spectra US-005
# @spectra OP-001
# @spectra OP-004
# @spectra WF-001
# @spectra INV-004
# @spectra EVT-001
# @spectra BR-008
# @spectra INV-005
"""Family-scoped receipt commands, persistence and purchase projections."""
import os
import uuid
from datetime import date
from typing import Annotated
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from app.application.receipt_commands import validated_receipt, request_digest, project_confirmed
from app.application.receipt_ingestion import ReceiptIngestionService
from app.core.auth import current_family
from app.domain.receipts.models import ParsedReceipt
from app.infrastructure.db.orm import Base, Family, Receipt, ReceiptSubmission, InventoryEntry
from app.infrastructure.db.session import create_db_engine, create_session_factory
from app.infrastructure.db.migrations import initialize_database
from app.infrastructure.parsers.registry import registry

class ParseRequest(BaseModel):
    ocr_text: str = Field(max_length=500000)

def receipt_view(receipt):
    return {"id": str(receipt.id), "purchase_date": receipt.purchase_date,
            "total_amount": format(receipt.total_amount, ".2f") if receipt.total_amount is not None else None,
            "total_vat": format(receipt.total_vat, ".2f") if receipt.total_vat is not None else None,
            "status": receipt.status,
            "lines": [{"line_number": x.line_number, "description": x.description,
                       "quantity": format(x.quantity, ".3f"), "unit": x.unit, "line_total": format(x.line_total, ".2f"),
                       "product_id": str(x.product_id) if x.product_id else None}
                      for x in sorted(receipt.lines, key=lambda row: row.line_number)]}

def create_app(database_url=None, jwt_secret=None, *, initialize_schema=False, shopping_collector=None, ocr_provider=None):
    api = FastAPI(title="Family Ledger API", version="0.4.1", description="Cada euro tiene un propósito.")
    @api.middleware("http")
    async def private_cache_policy(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response
    url = database_url or os.environ.get("DATABASE_URL")
    api.state.jwt_secret = jwt_secret if jwt_secret is not None else os.environ.get("JWT_SECRET")
    api.state.engine = create_db_engine(url) if url else None
    api.state.sessions = create_session_factory(api.state.engine) if api.state.engine else None
    if initialize_schema and api.state.engine is not None:
        initialize_database(api.state.engine)

    def database():
        if api.state.sessions is None:
            raise HTTPException(503, "Database is not configured")
        with api.state.sessions() as session:
            try:
                yield session
            except SQLAlchemyError:
                session.rollback()
                raise HTTPException(503, "Database operation could not complete") from None

    def require_family(session, family_id):
        if session.get(Family, family_id) is None:
            raise HTTPException(403, "Family is not provisioned")

    def find_receipt(session, family_id, receipt_id, *, lock=False):
        statement = select(Receipt).where(Receipt.id == receipt_id, Receipt.family_id == family_id)
        if lock:
            statement = statement.with_for_update()
        row = session.execute(statement).scalar_one_or_none()
        if row is None:
            raise HTTPException(404, "Receipt not found")
        return row

    def lookup_key(session, family_id, key, digest):
        submission = session.execute(select(ReceiptSubmission).where(ReceiptSubmission.family_id == family_id, ReceiptSubmission.key == key)).scalar_one_or_none()
        if submission is not None:
            if submission.request_digest != digest:
                raise HTTPException(409, "Idempotency key already used for a different request")
            return find_receipt(session, family_id, submission.receipt_id)
        return None

    def save_command(session, family_id, key, parsed, receipt_id=None):
        digest = request_digest(f"confirm:{receipt_id}" if receipt_id else "create", parsed)
        try:
            with session.begin():
                require_family(session, family_id)
                previous = lookup_key(session, family_id, key, digest)
                if previous is not None:
                    return receipt_view(previous)
                service = ReceiptIngestionService(session)
                if receipt_id is not None:
                    receipt = find_receipt(session, family_id, receipt_id, lock=True)
                    # A concurrent confirmation may have committed while this
                    # transaction waited for the receipt row lock.
                    previous = lookup_key(session, family_id, key, digest)
                    if previous is not None:
                        return receipt_view(previous)
                    if receipt.status != "pending_review":
                        raise HTTPException(409, "Only pending receipts can be confirmed")
                    if parsed.pending_fields:
                        raise HTTPException(422, "Resolve pending fields before confirmation")
                    service.update_pending(receipt, parsed, family_id)
                else:
                    result = service.ingest(parsed, family_id)
                    receipt = session.get(Receipt, result.receipt_id)
                project_confirmed(session, receipt)
                session.add(ReceiptSubmission(family_id=family_id, key=key, request_digest=digest,
                    receipt_id=receipt.id, payload=parsed.model_dump(mode="json")))
                session.flush()
                view = receipt_view(receipt)
            return view
        except IntegrityError:
            session.rollback()
            with session.begin():
                previous = lookup_key(session, family_id, key, digest)
                if previous is not None:
                    return receipt_view(previous)
            raise HTTPException(409, "Conflicting receipt operation; retry with the same key") from None

    def validate(value):
        try:
            return validated_receipt(value)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @api.post("/api/v1/receipts/parse", response_model=ParsedReceipt)
    def parse_receipt(body: ParseRequest):
        return registry.parse(body.ocr_text)

    @api.post("/api/v1/receipts", status_code=201)
    def create_receipt(body: ParsedReceipt, family_id: uuid.UUID = Depends(current_family),
                       session: Session = Depends(database),
                       idempotency_key: Annotated[str, Header(min_length=1, max_length=128)] = ""):
        if not idempotency_key:
            raise HTTPException(422, "Idempotency-Key is required")
        return save_command(session, family_id, idempotency_key, validate(body))

    @api.post("/api/v1/receipts/{receipt_id}/confirm")
    def confirm_receipt(receipt_id: uuid.UUID, body: ParsedReceipt,
                        family_id: uuid.UUID = Depends(current_family), session: Session = Depends(database),
                        idempotency_key: Annotated[str, Header(min_length=1, max_length=128)] = ""):
        if not idempotency_key:
            raise HTTPException(422, "Idempotency-Key is required")
        return save_command(session, family_id, idempotency_key, validate(body), receipt_id)

    @api.get("/api/v1/receipts")
    def list_receipts(family_id: uuid.UUID = Depends(current_family), session: Session = Depends(database),
                      limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
        require_family(session, family_id)
        rows = session.execute(select(Receipt).where(Receipt.family_id == family_id)
                 .order_by(Receipt.created_at, Receipt.id).limit(limit).offset(offset)).scalars().all()
        return [receipt_view(row) for row in rows]

    @api.get("/api/v1/receipts/{receipt_id}")
    def get_receipt(receipt_id: uuid.UUID, family_id: uuid.UUID = Depends(current_family), session: Session = Depends(database)):
        require_family(session, family_id)
        return receipt_view(find_receipt(session, family_id, receipt_id))

    @api.get("/api/v1/inventory")
    def inventory(family_id: uuid.UUID = Depends(current_family), session: Session = Depends(database),
                  limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
        require_family(session, family_id)
        rows = session.execute(select(InventoryEntry).where(InventoryEntry.family_id == family_id)
                      .order_by(InventoryEntry.created_at, InventoryEntry.id).limit(limit).offset(offset)).scalars().all()
        return {"projection": "confirmed_purchases_not_consumption_balance", "items": [
            {"id": str(row.id), "description": row.description, "quantity": format(row.quantity, ".3f"),
             "unit": row.unit, "expiry_date": row.expiry_date} for row in rows]}

    @api.get("/api/v1/analytics")
    def analytics(family_id: uuid.UUID = Depends(current_family), session: Session = Depends(database),
                  start: date | None = None, end: date | None = None):
        require_family(session, family_id)
        if start and end and start > end:
            raise HTTPException(422, "start must not be after end")
        stmt = select(Receipt).where(Receipt.family_id == family_id)
        if start:
            stmt = stmt.where(Receipt.purchase_date >= start)
        if end:
            stmt = stmt.where(Receipt.purchase_date <= end)
        rows = session.execute(stmt).scalars().all()
        confirmed = [x for x in rows if x.status == "confirmed" and x.purchase_date is not None]
        return {"confirmed_count": len(confirmed), "confirmed_total": format(sum((x.total_amount for x in confirmed if x.total_amount is not None), 0), ".2f"),
                "pending_count": sum(x.status == "pending_review" for x in rows), "period_excludes_undated": bool(start or end)}

    @api.get("/health")
    def health():
        return {"status": "ok"}
    from app.api.access import install_access_routes
    install_access_routes(api, database)
    from app.api.dashboard import install_dashboard_routes
    install_dashboard_routes(api, database)
    from app.api.capture import install_capture_routes
    install_capture_routes(api, database, ocr_provider)
    from app.api.shopping import install_shopping_routes
    install_shopping_routes(api, database, shopping_collector)
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles
    web_dir = Path(os.environ.get("SHOPPING_WEB_DIR", str(Path(__file__).resolve().parents[1] / "web" / "dist")))
    if web_dir.is_dir() and (web_dir / "index.html").is_file():
        api.mount("/", StaticFiles(directory=web_dir, html=True), name="shopping-web")
    return api

app = create_app()
