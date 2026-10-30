import asyncio
import hmac
import logging
import socket
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import iterate_in_threadpool

from app import db, s3
from app.config import settings

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_NAME_LENGTH = 300

JPEG = "image/jpeg"
PNG = "image/png"
WEBP = "image/webp"
EXTENSIONS = {JPEG: ".jpg", PNG: ".png", WEBP: ".webp"}


class ProductOut(BaseModel):
    id: uuid.UUID
    name: str
    image_url: str


def image_url(product_id: uuid.UUID) -> str:
    return f"/api/products/{product_id}/image"


def detect_image(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return JPEG
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return WEBP
    return None


def check_bot_token(header: str | None) -> None:
    if header is None or not hmac.compare_digest(header, settings.bot_secret):
        raise HTTPException(status_code=401, detail="invalid bot token")


async def ensure_bucket() -> None:
    last_error: Exception | None = None
    for attempt in range(1, 21):
        try:
            await asyncio.to_thread(s3.ensure_bucket)
            return
        except Exception as exc:
            last_error = exc
            logger.warning("minio is not ready (attempt %s): %s", attempt, exc)
            await asyncio.sleep(1)
    assert last_error is not None
    raise last_error


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(level=logging.INFO)
    await db.connect()
    await ensure_bucket()
    yield
    await db.close()


app = FastAPI(title="Каталог", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    try:
        await db.get_pool().fetchval("SELECT 1")
        ready = await asyncio.to_thread(s3.bucket_ready)
    except Exception as exc:
        logger.warning("health check failed: %s", exc)
        raise HTTPException(status_code=503, detail="not ready") from None
    if not ready:
        raise HTTPException(status_code=503, detail="not ready")
    return {"status": "ok", "instance": socket.gethostname()}


@app.get("/products", response_model=list[ProductOut])
async def list_products(limit: int = Query(default=100, ge=1, le=100)) -> list[ProductOut]:
    rows = await db.get_pool().fetch(
        """
        SELECT id, name
        FROM products
        ORDER BY created_at DESC
        LIMIT $1
        """,
        limit,
    )
    return [
        ProductOut(id=row["id"], name=row["name"], image_url=image_url(row["id"]))
        for row in rows
    ]


@app.get("/products/{product_id}/image")
async def get_product_image(product_id: uuid.UUID) -> StreamingResponse:
    row = await db.get_pool().fetchrow(
        "SELECT object_key, content_type FROM products WHERE id = $1",
        product_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="product not found")
    return StreamingResponse(
        iterate_in_threadpool(s3.object_chunks(row["object_key"])),
        media_type=row["content_type"],
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.post("/products", response_model=ProductOut, status_code=201)
async def create_product(
    name: str = Form(),
    file: UploadFile = File(),
    x_bot_token: str | None = Header(default=None),
) -> ProductOut:
    check_bot_token(x_bot_token)
    title = name.strip()
    if not title or len(title) > MAX_NAME_LENGTH:
        raise HTTPException(status_code=400, detail="invalid name")

    data = await file.read(MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="invalid image size")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="invalid image size")
    content_type = detect_image(data)
    if content_type is None:
        raise HTTPException(status_code=400, detail="unsupported image type")

    product_id = uuid.uuid4()
    object_key = f"{product_id}{EXTENSIONS[content_type]}"
    await asyncio.to_thread(s3.put_object, object_key, data, content_type)
    try:
        await db.get_pool().execute(
            """
            INSERT INTO products (id, name, object_key, content_type)
            VALUES ($1, $2, $3, $4)
            """,
            product_id,
            title,
            object_key,
            content_type,
        )
    except Exception:
        await asyncio.to_thread(s3.delete_object, object_key)
        logger.exception("failed to save product %s", product_id)
        raise HTTPException(status_code=500, detail="failed to save product") from None

    return ProductOut(id=product_id, name=title, image_url=image_url(product_id))
