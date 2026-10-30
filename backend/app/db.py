import asyncio
import logging

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

pool: asyncpg.Pool | None = None


async def connect() -> None:
    global pool
    last_error: Exception | None = None
    for attempt in range(1, 21):
        try:
            pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
            async with pool.acquire() as connection:
                await connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS products_created_at_idx
                    ON products (created_at DESC)
                    """
                )
            return
        except Exception as exc:
            last_error = exc
            logger.warning("postgres is not ready (attempt %s): %s", attempt, exc)
            await asyncio.sleep(1)
    assert last_error is not None
    raise last_error


async def close() -> None:
    global pool
    if pool is not None:
        await pool.close()
        pool = None


def get_pool() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("database pool is not ready")
    return pool
