import asyncio
import csv
import os
import uuid
from io import StringIO
from core.parser.base import BaseParser, ParseContent
from core.minio import MinioClient
from config.settings import settings


class MinerUParser(BaseParser):
    """基于 MinerU 的解析器"""

    def __init__(self):
        self.ext = None
        self.minio_client = MinioClient()
        self._initialized = False

    async def _ensure_init(self):
        """确保 MinIO 客户端已初始化"""
        if not self._initialized:
            await self.minio_client.init()
            self._initialized = True

    def supported_types(self) -> list:
        return ["pdf", "docx", "pptx", "xlsx", "txt", "md", "csv"]

    async def _process_file(self, file_path: str, file_id: int) -> dict:
        """
        处理文件并上传到 MinIO

        Args:
            file_path: 本地文件路径
            file_id: 文件ID

        Returns:
            dict: {
                "content": 解析后的内容,
                "minio_key": 原始文件的 MinIO 路径,
                "parsed_minio_key": 解析后文件的 MinIO 路径,
                "metadata_images": 图片列表
            }
        """
        # 确保 MinIO 客户端已初始化
        await self._ensure_init()

        file_name = os.path.basename(file_path)
        file_uuid = str(uuid.uuid4())

        # 1. 上传原始文件到 MinIO
        original_minio_key = f"documents/{file_uuid}/original/{file_name}"
        await self.minio_client.upload_file(
            bucket_name=settings.MINIO_BUCKET,
            object_name=original_minio_key,
            file_path=file_path
        )

        # 2. 解析到项目 resources 目录（避免污染用户目录）
        from config.settings import BASE_DIR
        temp_dir = os.path.join(BASE_DIR, "resources", "parsed", file_uuid)
        os.makedirs(temp_dir, exist_ok=True)

        cmd = [
            "mineru",
            "-p", file_path,
            "-o", temp_dir,
            "-b", "pipeline",
            "-m", "auto"
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"MinerU 解析失败: {stderr.decode()}")

        # 3. 读取生成的 .md 文件（自动检测输出目录）
        file_base_name = os.path.splitext(file_name)[0]
        parsed_dir = os.path.join(temp_dir, file_base_name)

        # 查找实际的输出目录（auto/office/...）
        md_file = None
        images_dir = None
        if os.path.exists(parsed_dir):
            for subdir in os.listdir(parsed_dir):
                subdir_path = os.path.join(parsed_dir, subdir)
                if os.path.isdir(subdir_path):
                    potential_md = os.path.join(subdir_path, f"{file_base_name}.md")
                    if os.path.exists(potential_md):
                        md_file = potential_md
                        images_dir = os.path.join(subdir_path, "images")
                        break

        if md_file is None:
            raise Exception(f"未找到解析后的 .md 文件，目录结构: {os.listdir(parsed_dir) if os.path.exists(parsed_dir) else '目录不存在'}")

        # 尝试多种编码
        encodings = ["utf-8", "gbk", "gb2312", "gb18030", "latin-1"]
        content = None
        for encoding in encodings:
            try:
                with open(md_file, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            raise Exception("无法识别输出文件编码")

        # 4. 上传图片到 metadata 目录
        metadata_images = []
        if images_dir and os.path.exists(images_dir):
            for img_file in os.listdir(images_dir):
                img_path = os.path.join(images_dir, img_file)
                if os.path.isfile(img_path):
                    img_minio_key = f"documents/{file_uuid}/metadata/{img_file}"
                    await self.minio_client.upload_file(
                        bucket_name=settings.MINIO_BUCKET,
                        object_name=img_minio_key,
                        file_path=img_path
                    )
                    metadata_images.append({
                        "name": img_file,
                        "minio_key": img_minio_key
                    })

        # 5. 上传解析后的 .md 文件到 MinIO
        parsed_minio_key = f"documents/{file_uuid}/parsed/{file_base_name}.md"
        await self.minio_client.upload_data(
            bucket_name=settings.MINIO_BUCKET,
            object_name=parsed_minio_key,
            data=content.encode("utf-8"),
            content_type="text/markdown"
        )

        # 6. 清理临时目录
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

        return {
            "content": content,
            "minio_key": original_minio_key,
            "parsed_minio_key": parsed_minio_key,
            "metadata_images": metadata_images
        }

    async def parse(self, file_path: str, file_id: int = None) -> ParseContent:
        """
        解析文件并上传到 MinIO

        Args:
            file_path: 本地文件路径
            file_id: 文件ID（可选）

        Returns:
            ParseContent: 解析结果
        """
        # 确保 MinIO 客户端已初始化
        await self._ensure_init()

        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1].lower().replace(".", "")
        file_uuid = str(uuid.uuid4())

        # txt/md/csv 文件直接存储，不调用 MinerU
        if file_ext in ["txt", "md", "csv"]:
            return await self._process_text_file(file_path, file_id, file_name, file_ext, file_uuid)

        # 其他文件调用 MinerU 解析
        minio_result = await self._process_file(file_path, file_id)

        return ParseContent(
            content=minio_result["content"],
            file_name=file_name,
            file_type=file_ext,
            metadata={
                "source": "mineru",
                "minio_key": minio_result["minio_key"],
                "parsed_minio_key": minio_result["parsed_minio_key"],
                "metadata_images": minio_result["metadata_images"]
            }
        )

    async def _process_text_file(self, file_path: str, file_id: int, file_name: str, file_ext: str, file_uuid: str) -> ParseContent:
        """
        处理 txt/csv/md 文件，统一转换为 Markdown 格式

        Args:
            file_path: 本地文件路径
            file_id: 文件ID
            file_name: 文件名
            file_ext: 文件扩展名
            file_uuid: 文件 UUID

        Returns:
            ParseContent: 解析结果
        """
        # 尝试多种编码读取文件
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
            # CSV 转换为 Markdown 表格
            markdown_content = self._csv_to_markdown(content, file_name)
        elif file_ext == "txt":
            # TXT 添加标题
            title = os.path.splitext(file_name)[0]
            markdown_content = f"# {title}\n\n{content}"
        else:
            # MD 直接使用
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
        """
        将 CSV 内容转换为 Markdown 表格

        Args:
            csv_content: CSV 内容
            file_name: 文件名

        Returns:
            str: Markdown 格式的表格
        """
        # 解析 CSV
        reader = csv.reader(StringIO(csv_content))
        rows = list(reader)

        if not rows:
            return f"# {os.path.splitext(file_name)[0]}\n\n空文件"

        # 获取标题
        title = os.path.splitext(file_name)[0]

        # 构建 Markdown 表格
        markdown_lines = [f"# {title}\n"]

        # 表头
        header = rows[0]
        markdown_lines.append("| " + " | ".join(header) + " |")
        markdown_lines.append("| " + " | ".join(["---"] * len(header)) + " |")

        # 数据行
        for row in rows[1:]:
            # 确保每行列数一致
            while len(row) < len(header):
                row.append("")
            markdown_lines.append("| " + " | ".join(row[:len(header)]) + " |")

        return "\n".join(markdown_lines)