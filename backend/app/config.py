from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    catalog_prompt: bool = False
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'listpilot.db').as_posix()}"
    upload_dir: Path = BACKEND_DIR / "data" / "uploads"
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
