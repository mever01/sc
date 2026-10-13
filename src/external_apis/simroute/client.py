import logging
import time

import httpx

from src.config.simroute import simroute_settings
from .errors import (
    SimrouteAuthError,
    SimrouteBalanceError,
    SimrouteError,
    SimrouteNoNumbersError,
    SimrouteTimeoutError,
)
from .schemas import ActivationNumber, SmsStatusResult

logger = logging.getLogger(__name__)


class SimrouteApiClient:
    """HTTP client for Simroute HandlerApiController using JSON API."""

    STATUS_PHONE_READY = 1
    STATUS_RETRY = 3
    STATUS_FINISH = 6
    STATUS_CANCEL = 8

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.base_url = (base_url or simroute_settings.base_url).strip()
        self.api_key = (api_key or simroute_settings.api_key).strip()
        self._client = httpx.Client(
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    def _get(self, action: str, **params) -> httpx.Response:
        """Send a GET request to the API endpoint."""
        query_params = {
            "action": action,
            "api_key": self.api_key,
            **{k: v for k, v in params.items() if v is not None},
        }
        try:
            response = self._client.get(self.base_url, params=query_params)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP error from Simroute API (%s): %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise SimrouteError(
                f"HTTP error {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Network error connecting to Simroute API: %s", exc)
            raise SimrouteError(f"Network error: {exc}") from exc

    def get_balance(self) -> float:
        """Return current account balance."""
        response = self._get("getBalance")
        data = response.json()
        status = data.get("status")
        if status == "ACCESS_BALANCE":
            return float(data.get("amount", 0.0))
        if status in ("BAD_KEY", "NO_KEY"):
            raise SimrouteAuthError(f"Authentication failed: {status}")
        raise SimrouteError(f"Unexpected getBalance response: {data}")

    def get_phone_number(
        self,
        service: str | None = None,
        country: int | None = None,
        pool_name: str | None = None,
        provider: int | None = None,
    ) -> ActivationNumber:
        """Request a new phone number for SMS activation."""
        service = service or simroute_settings.service_code
        country = country if country is not None else simroute_settings.country_id
        pool_name = pool_name or simroute_settings.pool_name
        provider = provider or simroute_settings.provider_id

        logger.info(
            "Requesting phone number: service=%r, country=%s, pool_name=%s, provider=%s",
            service,
            country,
            pool_name,
            provider,
        )

        response = self._get(
            "getNumber",
            service=service,
            country=country,
            pool_name=pool_name,
            provider=provider,
        )
        data = response.json()

        if isinstance(data, dict):
            status = data.get("status")
            if status == "ACCESS_NUMBER":
                activation = ActivationNumber(
                    activation_id=str(data["activationId"]),
                    phone=str(data["phone"]),
                    provider_id=data.get("providerId"),
                    operator_name=data.get("operatorName"),
                )
                logger.info(
                    "Number received: activation_id=%s, phone=%s (operator=%s)",
                    activation.activation_id,
                    activation.phone,
                    activation.operator_name,
                )
                return activation
            if status == "NO_NUMBERS":
                raise SimrouteNoNumbersError("No numbers available for this service/country")
            if status == "NO_BALANCE_FORWARD":
                raise SimrouteBalanceError("Insufficient Simroute balance")
            if status in ("BAD_KEY", "NO_KEY"):
                raise SimrouteAuthError(f"Invalid API key: {status}")
            raise SimrouteError(
                f"getNumber error: {status} (reason: {data.get('reason')})"
            )

        raise SimrouteError(f"Unexpected response format: {data}")

    def get_status(self, activation_id: str | int) -> SmsStatusResult:
        """Poll the current activation status and return any SMS code received."""
        response = self._get("getStatus", id=str(activation_id))
        data = response.json()

        if isinstance(data, dict):
            status = data.get("status", "")
            code = data.get("code")
            reason = data.get("reason")
            return SmsStatusResult(status=status, code=code, reason=reason)

        raise SimrouteError(f"Unexpected getStatus response format: {data}")

    def set_status(self, activation_id: str | int, status: int) -> bool:
        """Update activation status.

        Status codes:
            1 – PHONE_READY (ready to receive SMS)
            3 – RETRY (request another code)
            6 – FINISH (activation completed successfully)
            8 – CANCEL (cancel and refund)
        """
        names = {1: "PHONE_READY", 3: "RETRY", 6: "FINISH", 8: "CANCEL"}
        logger.info(
            "Setting activation %s status -> %s (%s)",
            activation_id,
            status,
            names.get(status, "UNKNOWN"),
        )
        response = self._get("setStatus", id=str(activation_id), status=status)
        return response.status_code == 200

    def cancel_activation(self, activation_id: str | int) -> bool:
        """Cancel activation and refund balance (status 8)."""
        return self.set_status(activation_id, self.STATUS_CANCEL)

    def finish_activation(self, activation_id: str | int) -> bool:
        """Mark activation as completed successfully (status 6)."""
        return self.set_status(activation_id, self.STATUS_FINISH)

    def wait_for_sms(
        self,
        activation_id: str | int,
        timeout: int | None = None,
        poll_interval: int | None = None,
    ) -> str:
        """Block until SMS verification code arrives or timeout expires.

        Uses time.monotonic() to ensure steady, clock-drift-resistant timeout tracking.
        """
        timeout = timeout or simroute_settings.sms_wait_timeout
        poll_interval = poll_interval or simroute_settings.sms_poll_interval
        deadline = time.monotonic() + timeout

        logger.info(
            "Waiting for SMS on activation %s (timeout=%ss, poll=%ss)...",
            activation_id,
            timeout,
            poll_interval,
        )

        while time.monotonic() < deadline:
            remaining = int(deadline - time.monotonic())
            result = self.get_status(activation_id)
            logger.info(
                "Activation %s status=%s | code=%s | remaining=%ss",
                activation_id,
                result.status,
                result.code,
                remaining,
            )

            if result.code:
                logger.info("SMS code received: %s", result.code)
                return result.code

            if result.status == "STATUS_CANCEL":
                raise SimrouteError(f"Activation {activation_id} was cancelled")

            time.sleep(poll_interval)

        raise SimrouteTimeoutError(
            f"Timed out after {timeout}s waiting for SMS on activation {activation_id}"
        )

    def close(self) -> None:
        """Close underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
