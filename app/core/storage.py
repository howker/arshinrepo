import io
import logging
from minio import Minio
from minio.error import S3Error
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class StorageClient:
    @property
    def client(self) -> Minio:
        if not hasattr(self, "_client"):
            settings = get_settings()
            self._client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
        return self._client

    def ensure_bucket_exists(self, bucket_name: str):
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"Created MinIO bucket: {bucket_name}")
        except S3Error as e:
            logger.error(f"MinIO Ensure Bucket Error: {e}")

    def upload_file(self, bucket_name: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self.ensure_bucket_exists(bucket_name)
        self.client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type
        )
        return object_name

storage = StorageClient()
