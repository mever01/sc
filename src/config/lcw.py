"""LC Waikiki target website settings."""

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LCWSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LCW_",
        extra="ignore",
    )

    domain: str = "www.lcwaikiki.iq"
    scheme: str = "https"
    register_path: str = "/en/register"

    @computed_field
    @property
    def register_url(self) -> str:
        """Build the registration URL from the configured domain parts."""
        domain = self.domain.strip().rstrip("/")
        path = self.register_path.strip().lstrip("/")
        scheme = self.scheme.strip()
        if not domain.startswith(("http://", "https://")):
            return f"{scheme}://{domain}/{path}"
        return f"{domain}/{path}"


lcw_settings = LCWSettings()
