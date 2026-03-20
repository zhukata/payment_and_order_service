from loguru import logger

from app.api.dependencies import build_payment_service
from app.infrastructure.db import db_session
from app.logging import configure_logging


def sync_pending_acquiring_payments() -> int:
    configure_logging()
    with db_session() as db:
        service = build_payment_service(db)
        synced = service.sync_pending_payments()
        logger.info("Synced pending acquiring payments: {}", len(synced))
        return len(synced)


if __name__ == "__main__":
    count = sync_pending_acquiring_payments()
    print(f"Synced payments: {count}")
