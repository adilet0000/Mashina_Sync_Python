import logging
import sys

from app.config import Settings


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=settings.normalized_log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )
