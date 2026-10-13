"""Simroute SMS API settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class SimrouteSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SIMROUTE_",
        extra="ignore",
    )

    base_url: str = "https://simroute.pro/api/stubs/handler_api.php"
    api_key: str = ""
    country_id: int = 47       # 47 = Iraq (+964)
    service_code: str = "lcw"  # lcw = LC Waikiki
    pool_name: str | None = None
    provider_id: int | None = None
    sms_wait_timeout: int = 180  # seconds
    sms_poll_interval: int = 4   # seconds


simroute_settings = SimrouteSettings()
