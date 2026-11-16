"""Send waiting bills to Ollama. Bills keep waiting while the PC is off, so this
can run on a schedule or with --loop next to the web server."""

import logging
import time
from typing import Any

from django.core.management.base import BaseCommand

from bills.models import Bill
from bills.reading import OllamaUnavailable, read_with_ollama

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Read bills that are waiting for the Ollama model."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--loop", action="store_true", help="Keep checking.")
        parser.add_argument(
            "--interval", type=int, default=300, help="Seconds between checks."
        )

    def handle(self, *args: Any, **options: Any) -> None:
        while True:
            self._read_waiting()
            if not options["loop"]:
                return
            time.sleep(options["interval"])

    def _read_waiting(self) -> None:
        waiting = Bill.objects.filter(status=Bill.Status.WAITING, lines=None).exclude(
            file=""
        )
        for bill in waiting:
            try:
                read_with_ollama(bill)
            except OllamaUnavailable as exc:
                # No point trying the other bills until the next round.
                logger.warning("Bills keep waiting for Ollama: %s", exc)
                return
            # One bad bill must not stop the others or crash the worker.
            except Exception:
                logger.exception("Couldn't read bill %s", bill.pk)
