"""Read a bill: a PDF with real text, in plain Python (D21: no AI)."""

import logging
from typing import BinaryIO

import pdfplumber
from django.utils.translation import gettext as _

from bills.models import Bill
from bills.parsing import parse_text
from bills.services import store_parsed_bill

logger = logging.getLogger(__name__)

# Bills run to a few pages; more is a wrong file, not a longer bill.
MAX_PAGES = 20


def pdf_text(handle: BinaryIO) -> str:
    """The text of a PDF, or "" when it has none or can't be opened."""
    try:
        with pdfplumber.open(handle) as pdf:
            return "\n".join(
                page.extract_text() or "" for page in pdf.pages[:MAX_PAGES]
            )
    # pdfminer raises many unrelated types on damaged files.
    except Exception:
        logger.warning("Couldn't read text from a PDF", exc_info=True)
        return ""


def read_text_pdf(bill: Bill, text: str | None = None) -> None:
    """Fill a new bill with the lines the reader recognises. A layout it doesn't
    know leaves the bill empty and failed, for typing the lines in. `text` is the
    PDF's text when the upload form already read it."""
    if text is None:
        try:
            with bill.file.open("rb") as handle:
                text = pdf_text(handle)
        except OSError:
            logger.warning("Couldn't open bill %s", bill.pk, exc_info=True)
            text = ""
    parsed = parse_text(text)
    if parsed.lines:
        store_parsed_bill(bill, parsed)
        return
    Bill.objects.filter(pk=bill.pk).update(
        status=Bill.Status.FAILED,
        error=_("This shop's layout isn't known yet: add the lines by hand."),
    )
