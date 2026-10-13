"""Playwright browser"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class BrowserSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    headless: bool = False
    browser_channel: str = "chrome"
    browser_timeout: int = 45_000  # milliseconds
    slow_mo: int = 80              # delay between actions (ms)
    max_captcha_retries: int = 10


browser_settings = BrowserSettings()
