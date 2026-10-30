import io
import logging

from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = logging.getLogger(__name__)

client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)


def ensure_bucket() -> None:
    if client.bucket_exists(settings.minio_bucket):
        return
    try:
        client.make_bucket(settings.minio_bucket)
    except S3Error as exc:
        if exc.code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise
        logger.info("bucket %s already exists", settings.minio_bucket)


def put_object(object_key: str, data: bytes, content_type: str) -> None:
    client.put_object(
        settings.minio_bucket,
        object_key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def bucket_ready() -> bool:
    return client.bucket_exists(settings.minio_bucket)


def object_chunks(object_key: str, chunk_size: int = 64 * 1024):
    response = client.get_object(settings.minio_bucket, object_key)
    try:
        for chunk in response.stream(chunk_size):
            yield chunk
    finally:
        response.close()
        response.release_conn()


def delete_object(object_key: str) -> None:
    try:
        client.remove_object(settings.minio_bucket, object_key)
    except S3Error as exc:
        if exc.code not in {"NoSuchKey", "NoSuchObject"}:
            raise
