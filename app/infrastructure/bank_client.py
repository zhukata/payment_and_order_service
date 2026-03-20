from dataclasses import dataclass
from datetime import datetime
import os

from loguru import logger
import requests

from app.domain.errors import ExternalServiceError


@dataclass
class BankCheckResult:
    bank_payment_id: str
    amount: int
    status: str
    paid_at: datetime | None


class BankClient:
    def __init__(
        self, base_url: str | None = None, timeout_sec: float = 5.0
    ) -> None:
        self.base_url = (
            base_url or os.getenv("BANK_API_BASE_URL", "https://bank.api")
        ).rstrip("/")
        self.timeout_sec = timeout_sec

    def start_payment(self, order_id: int, amount: int) -> str:
        payload = {"order_id": order_id, "amount": amount}
        url = f"{self.base_url}/acquiring_start"
        logger.info(
            "Starting acquiring payment in bank: order_id={}, amount={}",
            order_id,
            amount,
        )
        try:
            response = requests.post(
                url, json=payload, timeout=self.timeout_sec
            )
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            logger.exception("Bank start payment request failed")
            raise ExternalServiceError(
                f"Bank start payment request failed: {exc}"
            ) from exc
        except ValueError as exc:
            logger.exception("Bank start payment response JSON parse failed")
            raise ExternalServiceError(
                "Bank start payment response is not valid JSON"
            ) from exc

        bank_payment_id = body.get("bank_payment_id")
        error = body.get("error")
        if error:
            raise ExternalServiceError(f"Bank start payment error: {error}")
        if not bank_payment_id:
            raise ExternalServiceError(
                "Bank start payment response missing bank_payment_id"
            )

        logger.info("Bank payment created: bank_payment_id={}", bank_payment_id)
        return str(bank_payment_id)

    def check_payment(self, bank_payment_id: str) -> BankCheckResult:
        url = f"{self.base_url}/acquiring_check"
        logger.debug(
            "Checking bank payment status: bank_payment_id={}", bank_payment_id
        )
        try:
            response = requests.post(
                url,
                json={"bank_payment_id": bank_payment_id},
                timeout=self.timeout_sec,
            )
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            logger.exception("Bank check payment request failed")
            raise ExternalServiceError(
                f"Bank check payment request failed: {exc}"
            ) from exc
        except ValueError as exc:
            logger.exception("Bank check payment response JSON parse failed")
            raise ExternalServiceError(
                "Bank check payment response is not valid JSON"
            ) from exc

        if body.get("error"):
            raise ExternalServiceError(
                f"Bank check payment error: {body['error']}"
            )

        paid_at_raw = body.get("paid_at")
        paid_at = None
        if paid_at_raw:
            try:
                paid_at = datetime.fromisoformat(paid_at_raw)
            except ValueError as exc:
                raise ExternalServiceError(
                    "Bank check payment returned invalid paid_at"
                ) from exc

        try:
            amount = int(body["amount"])
            status = str(body["status"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ExternalServiceError(
                "Bank check payment response has invalid fields"
            ) from exc

        logger.debug(
            "Bank payment status received: bank_payment_id={}, status={}",
            bank_payment_id,
            status,
        )
        return BankCheckResult(
            bank_payment_id=str(body.get("bank_payment_id", bank_payment_id)),
            amount=amount,
            status=status,
            paid_at=paid_at,
        )
