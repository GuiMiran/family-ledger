"""Local image extraction port. OCR confidence is unknown unless measured."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OCRResult:
    text: str
    provider: str = "tesseract"
    confidence: float | None = None


class OCRProvider(Protocol):
    def extract(self, image: bytes) -> OCRResult: ...


class OCRError(Exception):
    """Public responses map types, never internal exception details."""


class OCRInvalidImage(OCRError): pass
class OCRImageTooLarge(OCRError): pass
class OCRUnavailable(OCRError): pass
class OCRTimeout(OCRError): pass
class OCRUnreadable(OCRError): pass
