import os
import sys

from loguru import logger


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO")
    logger.remove()
    logger.add(
        sys.stdout,
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=False,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS ZZ}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
    )
