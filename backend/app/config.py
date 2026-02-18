from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Paths for .env files
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_ROOT_ENV = _BACKEND_ROOT.parent / ".env"
_ENV_FILES = [_BACKEND_ROOT / ".env", _ROOT_ENV]

# Load .env with override=True so file values win over empty env vars
for _env_path in _ENV_FILES:
    if _env_path.exists():
        load_dotenv(_env_path, override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[f for f in _ENV_FILES if f.exists()] or _ENV_FILES[0],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nanonets_api_key: str = ""
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_pages: int = 5


def get_settings() -> Settings:
    return Settings()
