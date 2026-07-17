"""
MinerU API 解析器

通过 MinerU 云端 API 解析文档（PDF/Word/PPT/Excel/图片）
返回 Markdown 格式内容 + 图片
"""
import asyncio
import csv
import io
import os
import uuid
import zipfile
from io import StringIO
from typing import Optional

import httpx

from core.parser.base import BaseParser, ParseContent
from core.minio import MinioClient
from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)


class MinerUParser(BaseParser):
    """MinerU API 解析器"""

    def __init__(self):
        self.minio_client = MinioClient()
        self._initialized = False

    async def _ensure_init(self):
        """确保 MinIO 客户端已初始化"""
        if not self._initialized:
            await self.minio_client.init()
            self._initialized = True

    def supported_types(self) -> list:
        return ["pdf", "docx", "pptx", "xlsx", "txt", "md", "csv"]

    async def parse(self, file_path: str, file_id: int = None) -> ParseContent:
        """解析文件并上传到 MinIO"""
        await self._ensure_init()

        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1].lower().replace(".", "")
        file_uuid = str(uuid.uuid4())

        # txt/md/csv 文件直接存储，不调用 MinerU API
        if file_ext in ["txt", "md", "csv"]:
            return await self._process_text_file(file_path, file_id, file_name, file_ext, file_uuid)

        # 其他文件调用 MinerU API 解析
        return await self._parse_via_api(file_path, file_id, file_name, file_ext, file_uuid)

    async def _parse_via_api(self, file_path: str, file_id: int, file_name: str, file_ext: str, file_uuid: str) -> ParseContent:
        """通过 MinerU API 解析文件"""
        # 1. 上传原始文件到 MinIO
        original_minio_key = f"documents/{file_uuid}/original/{file_name}"
        await self.minio_client.upload_file(
            bucket_name=settings.MINIO_BUCKET,
            object_name=original_minio_key,
            file_path=file_path
        )

        # 2. 获取 MinIO presigned URL
        presigned_url = await self.minio_client.presigned_download_url(
            bucket_name=settings.MINIO_BUCKET,
            object_name=original_minio_key
        )

        # 3. 提交 MinerU API 解析任务
        task_id = await self._submit_task(presigned_url)
        if not task_id:
            raise Exception("MinerU API 提交任务失败")

        # 4. 轮询等待解析完成
        result = await self._poll_task(task_id)
        if not result or result.get("state") != "done":
            error_msg = result.get("err_msg", "未知错误") if result else "轮询超时"
            raise Exception(f"MinerU API 解析失败: {error_msg}")

        # 5. 下载解析结果 zip 包
        zip_url = result.get("full_zip_url")
        if not zip_url:
            raise Exception("MinerU API 未返回 zip 下载链接")

        markdown_content, image_files = await self._download_and_extract_zip(zip_url)

        # 6. 上传图片到 MinIO
        metadata_images = []
        for img_file in image_files:
            img_minio_key = f"documents/{file_uuid}/parsed/images/{img_file['name']}"
            await self.minio_client.upload_data(
                bucket_name=settings.MINIO_BUCKET,
                object_name=img_minio_key,
                data=img_file["data"],
                content_type="image/png"
            )
            metadata_images.append({
                "name": img_file["name"],
                "minio_key": img_minio_key
            })

        # 7. 上传解析后的 Markdown 到 MinIO
        parsed_minio_key = f"documents/{file_uuid}/parsed/{os.path.splitext(file_name)[0]}.md"
        await self.minio_client.upload_data(
            bucket_name=settings.MINIO_BUCKET,
            object_name=parsed_minio_key,
            data=markdown_content.encode("utf-8"),
            content_type="text/markdown"
        )

        logger.info(f"MinerU API 解析完成: {file_name}, 共 {len(metadata_images)} 张图片")

        return ParseContent(
            content=markdown_content,
            file_name=file_name,
            file_type=file_ext,
            metadata={
                "source": "mineru_api",
                "minio_key": original_minio_key,
                "parsed_minio_key": parsed_minio_key,
                "metadata_images": metadata_images
            }
        )

    async def _submit_task(self, file_url: str) -> Optional[str]:
        """提交 MinerU API 解析任务"""
        url = f"{settings.MINERU_API_BASE_URL}/extract/task"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.MINERU_API_TOKEN}"
        }
        data = {
            "url": file_url,
            "model_version": "vlm",
            "is_ocr": True,
            "enable_formula": True,
            "enable_table": True,
            "language": "ch"
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()

                if result.get("code") == 0:
                    task_id = result["data"]["task_id"]
                    logger.info(f"MinerU API 任务已提交: {task_id}")
                    return task_id
                else:
                    logger.error(f"MinerU API 提交失败: {result.get('msg')}")
                    return None
            except Exception as e:
                logger.error(f"MinerU API 提交异常: {e}")
                return None

    async def _poll_task(self, task_id: str) -> Optional[dict]:
        """轮询 MinerU API 任务状态"""
        url = f"{settings.MINERU_API_BASE_URL}/extract/task/{task_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.MINERU_API_TOKEN}"
        }

        timeout = settings.MINERU_TIMEOUT
        interval = settings.MINERU_POLL_INTERVAL
        elapsed = 0

        async with httpx.AsyncClient(timeout=30) as client:
            while elapsed < timeout:
                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    result = response.json()

                    if result.get("code") != 0:
                        logger.error(f"MinerU API 查询失败: {result.get('msg')}")
                        return None

                    state = result["data"].get("state")

                    if state == "done":
                        logger.info(f"MinerU API 解析完成: {task_id}")
                        return result["data"]
                    elif state == "failed":
                        error_msg = result["data"].get("err_msg", "未知错误")
                        logger.error(f"MinerU API 解析失败: {error_msg}")
                        return result["data"]
                    else:
                        logger.debug(f"MinerU API 解析中: {state} ({elapsed}s)")

                    await asyncio.sleep(interval)
                    elapsed += interval

                except Exception as e:
                    logger.error(f"MinerU API 轮询异常: {e}")
                    await asyncio.sleep(interval)
                    elapsed += interval

        logger.error(f"MinerU API 轮询超时: {task_id}")
        return None

    async def _download_and_extract_zip(self, zip_url: str):
        """下载并解压 MinerU API 返回的 zip 包"""
        markdown_content = ""
        image_files = []

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                response = await client.get(zip_url)
                response.raise_for_status()

                with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                    # 查找 full.md
                    for name in zf.namelist():
                        if name.endswith("full.md"):
                            markdown_content = zf.read(name).decode("utf-8")
                            break

                    # 查找图片文件
                    for name in zf.namelist():
                        if name.startswith("images/") and not name.endswith("/"):
                            img_name = os.path.basename(name)
                            img_data = zf.read(name)
                            image_files.append({
                                "name": img_name,
                                "data": img_data
                            })

                logger.info(f"MinerU zip 解压完成: {len(markdown_content)} 字符, {len(image_files)} 张图片")

            except Exception as e:
                logger.error(f"MinerU zip 下载失败: {e}")
                raise

        return markdown_content, image_files

    # ==================== 文本文件处理 ====================

    async def _process_text_file(self, file_path: str, file_id: int, file_name: str, file_ext: str, file_uuid: str) -> ParseContent:
        """处理 txt/csv/md 文件"""
        encodings = ["utf-8", "gbk", "gb2312", "gb18030", "latin-1"]
        content = None
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            raise Exception("无法识别文件编码")

        # 上传原始文件到 MinIO
        original_minio_key = f"documents/{file_uuid}/original/{file_name}"
        await self.minio_client.upload_file(
            bucket_name=settings.MINIO_BUCKET,
            object_name=original_minio_key,
            file_path=file_path
        )

        # 统一转换为 Markdown 格式
        if file_ext == "csv":
            markdown_content = self._csv_to_markdown(content, file_name)
        elif file_ext == "txt":
            title = os.path.splitext(file_name)[0]
            markdown_content = f"# {title}\n\n{content}"
        else:
            markdown_content = content

        # 存储为 Markdown 格式
        md_file_name = os.path.splitext(file_name)[0] + ".md"
        parsed_minio_key = f"documents/{file_uuid}/parsed/{md_file_name}"
        await self.minio_client.upload_data(
            bucket_name=settings.MINIO_BUCKET,
            object_name=parsed_minio_key,
            data=markdown_content.encode("utf-8"),
            content_type="text/markdown"
        )

        return ParseContent(
            content=markdown_content,
            file_name=file_name,
            file_type=file_ext,
            metadata={
                "source": "text",
                "minio_key": original_minio_key,
                "parsed_minio_key": parsed_minio_key,
                "parsed_images": []
            }
        )

    def _csv_to_markdown(self, csv_content: str, file_name: str) -> str:
        """将 CSV 内容转换为 Markdown 表格"""
        reader = csv.reader(StringIO(csv_content))
        rows = list(reader)

        if not rows:
            return f"# {os.path.splitext(file_name)[0]}\n\n空文件"

        title = os.path.splitext(file_name)[0]
        markdown_lines = [f"# {title}\n"]

        header = rows[0]
        markdown_lines.append("| " + " | ".join(header) + " |")
        markdown_lines.append("| " + " | ".join(["---"] * len(header)) + " |")

        for row in rows[1:]:
            while len(row) < len(header):
                row.append("")
            markdown_lines.append("| " + " | ".join(row[:len(header)]) + " |")

        return "\n".join(markdown_lines)
