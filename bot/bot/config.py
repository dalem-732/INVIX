import os
from dataclasses import dataclass


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: frozenset[int]
    webapp_url: str
    public_base_url: str
    bot_secret: str
    api_url: str
    database_url: str


def load_settings() -> Settings:
    admin_ids: set[int] = set()
    for part in _env("ADMIN_IDS").split(","):
        part = part.strip()
        if not part:
            continue
        admin_ids.add(int(part))
    return Settings(
        bot_token=_env("BOT_TOKEN"),
        admin_ids=frozenset(admin_ids),
        webapp_url=_env("WEBAPP_URL", "http://localhost"),
        public_base_url=_env("PUBLIC_BASE_URL").rstrip("/"),
        bot_secret=_env("BOT_SECRET"),
        api_url=_env("API_URL", "http://api:8000").rstrip("/"),
        database_url=_env("DATABASE_URL"),
    )


settings = load_settings()
