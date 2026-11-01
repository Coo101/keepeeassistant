"""Read a bill file: PDF text in plain Python, everything else through Ollama."""

import base64
import http.client
import io
import json
import logging
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

import pdfplumber
from django.conf import settings
from PIL import Image, ImageOps

from bills.models import Bill
from bills.parsing import ParsedBill, ParsedLine, parse_text, to_decimal
from bills.services import store_parsed_bill

logger = logging.getLogger(__name__)

MAX_PAGES = 5
MAX_IMAGE_SIDE = 1600
PROMPT = """This image is a shop bill. Read every purchased item and answer with JSON:
{"lines": [{"description": "text as printed", "quantity": 1, "line_total": 1.23}],
 "total": 12.34}
line_total is what was paid for that line, negative for a discount. Copy text as
printed and don't guess. Leave out names, addresses and card or loyalty numbers."""


class OllamaUnavailable(Exception):
    """Try again later: the PC is off, or the model isn't installed."""


class BillUnreadable(Exception):
    """Trying again won't help without changing something."""


def read_text_pdf(bill: Bill) -> bool:
    """Read a PDF that holds real text. False means it needs Ollama."""
    if not bill.file or Path(bill.file.name).suffix != ".pdf":
        return False
    try:
        with bill.file.open("rb") as handle, pdfplumber.open(handle) as pdf:
            text = "\n".join(
                page.extract_text() or "" for page in pdf.pages[: MAX_PAGES * 4]
            )
    # pdfminer raises many unrelated types on damaged files.
    except Exception:
        logger.warning("Couldn't read text from bill %s", bill.pk, exc_info=True)
        return False
    parsed = parse_text(text)
    if not parsed.lines:
        return False
    store_parsed_bill(bill, parsed)
    return True


def _page_images(bill: Bill) -> list[bytes]:
    images: list[Image.Image] = []
    with bill.file.open("rb") as handle:
        if Path(bill.file.name).suffix == ".pdf":
            with pdfplumber.open(handle) as pdf:
                images = [
                    page.to_image(resolution=200).original.copy()
                    for page in pdf.pages[:MAX_PAGES]
                ]
        else:
            images = [Image.open(handle).copy()]
    encoded = []
    for image in images:
        # Phones store portrait photos sideways, with a tag saying so.
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded.append(buffer.getvalue())
    return encoded


def _ask_ollama(image: bytes) -> dict:
    if not settings.OLLAMA_URL:
        raise OllamaUnavailable("OLLAMA_URL isn't set")
    request = urllib.request.Request(
        f"{settings.OLLAMA_URL.rstrip('/')}/api/generate",
        data=json.dumps(
            {
                "model": settings.OLLAMA_VISION_MODEL,
                "prompt": PROMPT,
                "images": [base64.b64encode(image).decode()],
                "stream": False,
                "format": "json",
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(
            request, timeout=settings.OLLAMA_TIMEOUT
        ) as response:
            return json.loads(json.loads(response.read())["response"])
    except (OSError, urllib.error.URLError, http.client.HTTPException) as exc:
        raise OllamaUnavailable(str(exc)) from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise BillUnreadable("The model's answer wasn't valid JSON.") from exc


def _parse_answer(answer: dict) -> ParsedBill:
    lines = []
    raw_lines = answer.get("lines") if isinstance(answer, dict) else None
    for raw in raw_lines if isinstance(raw_lines, list) else []:
        if not isinstance(raw, dict):
            continue
        total = to_decimal(raw.get("line_total"))
        description = str(raw.get("description") or "").strip()[:200]
        if total is None or not description or abs(total) >= 10_000_000:
            continue
        quantity = to_decimal(raw.get("quantity")) or Decimal("1")
        if not 0 < quantity < 10000:
            quantity = Decimal("1")
        lines.append(
            ParsedLine(
                description=description,
                quantity=quantity.quantize(Decimal("0.001")),
                line_total=total.quantize(Decimal("0.01")),
                is_other=total < 0,
            )
        )
    total = to_decimal(answer.get("total")) if isinstance(answer, dict) else None
    if total is not None and abs(total) >= 10_000_000:
        total = None
    return ParsedBill(
        lines=lines,
        printed_total=total.quantize(Decimal("0.01")) if total is not None else None,
    )


def read_with_ollama(bill: Bill) -> None:
    """Fill a waiting bill. Raises OllamaUnavailable if it can't be reached; the
    bill just stays waiting."""
    try:
        images = _page_images(bill)
    # Pillow and pdfium raise several types on damaged or oversized files.
    except Exception:
        logger.warning("Couldn't open bill %s", bill.pk, exc_info=True)
        _mark_failed(bill, "The file couldn't be opened. Add the lines by hand.")
        return
    lines: list[ParsedLine] = []
    printed_total = None
    try:
        for image in images:
            parsed = _parse_answer(_ask_ollama(image))
            lines.extend(parsed.lines)
            printed_total = parsed.printed_total or printed_total
    except BillUnreadable as exc:
        _mark_failed(bill, str(exc))
        return
    if not lines:
        _mark_failed(bill, "No lines were found. Add them by hand.")
        return
    store_parsed_bill(bill, ParsedBill(lines=lines, printed_total=printed_total))


def _mark_failed(bill: Bill, error: str) -> None:
    # Only while still waiting: someone may have added lines during the read.
    Bill.objects.filter(pk=bill.pk, status=Bill.Status.WAITING).update(
        status=Bill.Status.FAILED, error=error
    )
