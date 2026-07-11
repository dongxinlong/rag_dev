import logging
from typing import BinaryIO, Optional, List
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from anyio import to_thread
from config.settings import settings

logger = logging.getLogger(__name__)


class MinioClient:
    """
    异步 MinIO 客户端封装
    """

    def __init__(self):
        """初始化客户端，确保默认 bucket 存在"""
        self._client: Optional[Minio] = None        

    async def init(self) -> None:
        self._client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=settings.MINIO_SECURE,
        )
        await self.ensure_bucket(settings.MINIO_BUCKET)

    @property
    def client(self) -> Minio:
        if self._client is None:
            raise RuntimeError("MinIO client not initialized, call init() first")
        return self._client

    # ---------- Bucket ----------

    async def bucket_exists(self, bucket_name: str) -> bool:
        return await to_thread.run_sync(self.client.bucket_exists, bucket_name)

    async def ensure_bucket(self, bucket_name: str) -> None:
        exists = await self.bucket_exists(bucket_name)
        if not exists:
            await to_thread.run_sync(self.client.make_bucket, bucket_name)
            logger.info("Bucket created: %s", bucket_name)

    async def ensure_directory(self, bucket_name: str, dir_path: str) -> None:
        """确保目录存在（创建空目录对象）"""
        from io import BytesIO
        # 确保路径以 / 结尾
        dir_path = dir_path.rstrip("/") + "/"
        await to_thread.run_sync(
            self.client.put_object,
            bucket_name,
            dir_path,
            BytesIO(b""),
            0,
        )

    # ---------- Upload ----------

    async def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
        content_type: str = "application/octet-stream",
    ) -> None:
        """
        上传本地文件
        """
        await self.ensure_bucket(bucket_name)
        await to_thread.run_sync(
            self.client.fput_object,
            bucket_name,
            object_name,
            file_path,
            content_type,
        )

    async def upload_data(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """
        上传字节数据（内存文件）
        """
        from io import BytesIO

        await self.ensure_bucket(bucket_name)
        await to_thread.run_sync(
            self.client.put_object,
            bucket_name,
            object_name,
            BytesIO(data),
            len(data),
            content_type,
        )

    # ---------- Download ----------

    async def download_file(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
    ) -> None:
        """
        下载为本地文件
        """
        await to_thread.run_sync(
            self.client.fget_object,
            bucket_name,
            object_name,
            file_path,
        )

    async def get_object(
        self,
        bucket_name: str,
        object_name: str,
    ) -> bytes:
        """
        读取对象为字节
        """
        response = await to_thread.run_sync(
            self.client.get_object,
            bucket_name,
            object_name,
        )
        try:
            data = response.read()
            return data
        finally:
            response.close()
            response.release_conn()

    # ---------- Delete ----------

    async def remove_object(self, bucket_name: str, object_name: str) -> None:
        await to_thread.run_sync(
            self.client.remove_object,
            bucket_name,
            object_name,
        )

    async def remove_objects(self, bucket_name: str, object_names: List[str]) -> None:
        """
        批量删除
        """
        from minio.deleteobjects import DeleteObject

        delete_objs = [DeleteObject(name) for name in object_names]
        errors = await to_thread.run_sync(
            lambda: list(self.client.remove_objects(bucket_name, delete_objs))
        )

    # ---------- Presigned URL ----------

    async def presigned_upload_url(
        self,
        bucket_name: str,
        object_name: str,
        expires: int | None = None,
    ) -> str:
        """
        前端直传（PUT）
        """
        expires = expires or settings.MINIO_EXPIRY
        url = await to_thread.run_sync(
            lambda: self.client.presigned_put_object(
                bucket_name,
                object_name,
                expires=timedelta(seconds=expires),
            )
        )
        return url

    async def presigned_download_url(
        self,
        bucket_name: str,
        object_name: str,
        expires: int | None = None,
    ) -> str:
        """
        前端直签下载
        """
        expires = expires or settings.MINIO_EXPIRY
        url = await to_thread.run_sync(
            lambda: self.client.presigned_get_object(
                bucket_name,
                object_name,
                expires=timedelta(seconds=expires),
            )
        )
        return url

    # ---------- Stat ----------

    async def stat_object(self, bucket_name: str, object_name: str):
        return await to_thread.run_sync(
            self.client.stat_object,
            bucket_name,
            object_name,
        )