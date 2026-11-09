# @spectra BR-013
# @spectra INV-008
"""Bounded local Tesseract execution; no shell, uploads or image retention."""
from io import BytesIO
from pathlib import Path
import subprocess
import tempfile
import threading
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from app.domain.ocr import (OCRImageTooLarge, OCRInvalidImage, OCRResult,
    OCRTimeout, OCRUnavailable, OCRUnreadable)

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000
MAX_OCR_BYTES = 500_000
OCR_TIMEOUT_SECONDS = 20


def validate_image(data: bytes) -> None:
    if len(data) > MAX_IMAGE_BYTES:
        raise OCRImageTooLarge()
    valid_signature = (data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG\r\n\x1a\n")
                       or (data.startswith(b"RIFF") and data[8:12] == b"WEBP"))
    if not valid_signature:
        raise OCRInvalidImage()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise OCRInvalidImage()
                width, height = image.size
                if width * height > MAX_PIXELS:
                    raise OCRImageTooLarge()
                if width < 100 or height < 100 or getattr(image, "n_frames", 1) != 1:
                    raise OCRInvalidImage()
                image.verify()
            # Decode as well as verify: truncated image payloads cannot reach OCR.
            with Image.open(BytesIO(data)) as image:
                image.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise OCRImageTooLarge() from None
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise OCRInvalidImage() from None


class TesseractOCR:
    def extract(self, image: bytes) -> OCRResult:
        validate_image(image)
        with tempfile.TemporaryDirectory(prefix="ledger-ocr-") as directory:
            path = Path(directory) / "input.png"
            with Image.open(BytesIO(image)) as original:
                normalized = ImageOps.exif_transpose(original)
                try:
                    rgb = normalized.convert("RGB")
                    try:
                        rgb.info.clear()
                        rgb.save(path, format="PNG")
                    finally:
                        rgb.close()
                finally:
                    normalized.close()
            try:
                process = subprocess.Popen(
                    ["tesseract", str(path), "stdout", "-l", "spa+cat+eng", "--psm", "6"],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                    shell=False,
                )
            except OSError:
                raise OCRUnavailable() from None
            output = []
            read_failed = []

            def read_output():
                try:
                    output.append(process.stdout.read(MAX_OCR_BYTES + 1))
                    if len(output[0]) > MAX_OCR_BYTES:
                        process.kill()
                except OSError:
                    read_failed.append(True)

            reader = threading.Thread(target=read_output, daemon=True)
            reader.start()
            try:
                try:
                    process.wait(timeout=OCR_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise OCRTimeout() from None
            finally:
                reader.join(timeout=2)
                if process.poll() is None:
                    process.kill()
                    process.wait()
                process.stdout.close()
            if reader.is_alive() or read_failed or not output or len(output[0]) > MAX_OCR_BYTES:
                raise OCRUnreadable()
            if process.returncode != 0:
                raise OCRUnavailable()
            text = output[0].decode("utf-8", errors="replace").strip()
            if not text:
                raise OCRUnreadable()
            return OCRResult(text=text)
