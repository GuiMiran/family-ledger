# @spectra US-010
# @spectra BR-013
# @spectra INV-008
# @spectra OP-007
"""Authenticated draft extraction, without receipt or image persistence."""
import uuid
import threading

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.application.receipt_commands import validated_receipt
from app.core.auth import current_family
from app.domain.ocr import (OCRImageTooLarge, OCRInvalidImage, OCRTimeout,
    OCRUnavailable, OCRUnreadable)
from app.infrastructure.db.orm import Family
from app.infrastructure.ocr import MAX_IMAGE_BYTES, MAX_OCR_BYTES, TesseractOCR, validate_image
from app.infrastructure.parsers.registry import registry

WIRE_LIMIT = MAX_IMAGE_BYTES + 65536
RETAKE = "No se pudo leer el ticket. Haz otra foto nítida con el ticket completo."


class _UploadLimit(MultiPartException):
    pass


def install_capture_routes(api, database, ocr_provider=None):
    api.state.ocr_provider = ocr_provider if ocr_provider is not None else TesseractOCR()
    api.state.ocr_capacity = threading.BoundedSemaphore(1)

    @api.post("/api/v1/receipts/extract", openapi_extra={
        "requestBody": {"required": True, "content": {"multipart/form-data": {
            "schema": {"type": "object", "required": ["image"], "properties": {
                "image": {"type": "string", "format": "binary", "description": "JPEG/PNG/WebP up to 10 MiB; authenticated private draft extraction"}}}}}}})
    async def extract(request: Request, family_id: uuid.UUID = Depends(current_family),
                      session: Session = Depends(database)):
        if session.get(Family, family_id) is None:
            raise HTTPException(403, "Family is not provisioned")
        session.rollback()  # Release read transaction before decoding/processing an image.
        if not api.state.ocr_capacity.acquire(blocking=False):
            raise HTTPException(429, "Ya se está leyendo otra foto. Inténtalo en unos segundos.",
                                headers={"Retry-After": "5"})
        try:
            return await extract_image(request)
        finally:
            api.state.ocr_capacity.release()

    async def extract_image(request):
        if not request.headers.get("content-type", "").lower().startswith("multipart/form-data"):
            raise HTTPException(415, "Envía una foto JPEG, PNG o WebP. HEIC no es compatible.")
        try:
            length = int(request.headers.get("content-length", "0"))
        except ValueError:
            raise HTTPException(400, "Solicitud de foto no válida.") from None
        if length > WIRE_LIMIT:
            raise HTTPException(413, "La foto supera el límite de 10 MiB. Reduce su tamaño.")
        consumed = 0

        async def receive():
            nonlocal consumed
            message = await request.receive()
            consumed += len(message.get("body", b""))
            if consumed > WIRE_LIMIT:
                # Multipart parser closes its temporary files on MultiPartException.
                raise _UploadLimit("Image request exceeds limit")
            return message

        bounded = Request(request.scope, receive)
        try:
            async with bounded.form(max_files=1, max_fields=0, max_part_size=MAX_IMAGE_BYTES) as form:
                upload = form.get("image")
                if len(form) != 1 or not isinstance(upload, UploadFile):
                    raise HTTPException(422, "Selecciona una sola foto del ticket.")
                data = await upload.read(MAX_IMAGE_BYTES + 1)
        except StarletteHTTPException as exc:
            if consumed > WIRE_LIMIT:
                raise HTTPException(413, "La foto supera el límite de 10 MiB. Reduce su tamaño.") from None
            if exc.status_code == 400:
                raise HTTPException(400, "Selecciona una sola foto válida del ticket.") from None
            raise
        try:
            await run_in_threadpool(validate_image, data)
            result = await run_in_threadpool(api.state.ocr_provider.extract, data)
            if not isinstance(result.text, str) or len(result.text.encode("utf-8")) > MAX_OCR_BYTES:
                raise OCRUnreadable()
            parsed = registry.parse(result.text)
            if not parsed.lines:
                raise OCRUnreadable()
            parsed = validated_receipt(parsed)
        except OCRImageTooLarge:
            raise HTTPException(413, "La foto supera el límite de tamaño o resolución. Reduce su tamaño.") from None
        except OCRInvalidImage:
            raise HTTPException(415, "Usa una foto JPEG, PNG o WebP válida. HEIC no es compatible.") from None
        except OCRTimeout:
            raise HTTPException(504, "La lectura tardó demasiado. Prueba otra foto del ticket.") from None
        except OCRUnavailable:
            raise HTTPException(503, "La lectura de fotos no está disponible. Inténtalo más tarde.") from None
        except (OCRUnreadable, ValueError, ArithmeticError):
            raise HTTPException(422, RETAKE) from None
        return {"parsed_receipt": parsed.model_dump(mode="json"),
                "ocr": {"provider": result.provider, "confidence": None},
                "warnings": ["Revisa los campos pendientes antes de guardar."] if parsed.pending_fields else []}
