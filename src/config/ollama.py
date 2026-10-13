from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="OLLAMA_",
        extra="ignore",
    )

    enabled: bool = True
    base_url: str = "http://localhost:11434"
    url: str = "http://localhost:11434/api/generate"
    model: str = "glm-ocr:latest"
    timeout: float = 30.0

    @property
    def resolved_base_url(self) -> str:
        """Return normalized base URL for Ollama service."""
        target = self.base_url or self.url or "http://localhost:11434"
        clean = target.strip().rstrip("/")
        if "/api" in clean:
            clean = clean.split("/api")[0]
        return clean


ollama_settings = OllamaSettings()
