import os
from dataclasses import dataclass


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    database_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool
    bot_secret: str


def load_settings() -> Settings:
    settings = Settings(
        database_url=_env("DATABASE_URL"),
        minio_endpoint=_env("MINIO_ENDPOINT", "minio:9000"),
        minio_access_key=_env("MINIO_ACCESS_KEY"),
        minio_secret_key=_env("MINIO_SECRET_KEY"),
        minio_bucket=_env("MINIO_BUCKET", "products"),
        minio_secure=_env("MINIO_SECURE", "false").lower() == "true",
        bot_secret=_env("BOT_SECRET"),
    )
    missing = [
        name
        for name, value in (
            ("DATABASE_URL", settings.database_url),
            ("MINIO_ACCESS_KEY", settings.minio_access_key),
            ("MINIO_SECRET_KEY", settings.minio_secret_key),
            ("BOT_SECRET", settings.bot_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
    return settings


settings = load_settings()
