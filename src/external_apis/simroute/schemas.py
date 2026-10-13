from dataclasses import dataclass


@dataclass
class ActivationNumber:
    activation_id: str
    phone: str
    provider_id: int | None = None
    operator_name: str | None = None

    @property
    def national_number(self) -> str:
        """Return the phone number without the Iraq country code (964)."""
        raw = self.phone.lstrip("+").strip()
        if raw.startswith("964"):
            return raw[3:]
        return raw


@dataclass
class SmsStatusResult:
    status: str
    code: str | None = None
    reason: str | None = None
