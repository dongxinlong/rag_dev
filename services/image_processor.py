"""
图片处理服务

通用服务：处理文档中的图片，调用视觉模型替换为文字
支持所有文档类型（PDF、Word、扫描件等）
"""
import re
import os
from datetime import datetime
from typing import List, Tuple
from core.vision import vision_service
from core.minio import MinioClient
from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)


class ImageProcessor:
    """图片处理器"""

    def __init__(self):
        self.minio_client = MinioClient()

    def extract_image_references(self, content: str) -> List[Tuple[str, str]]:
        """
        提取文档中的图片引用

        支持两种格式：
        1. Markdown: ![alt](images/xxx.png)
        2. HTML: <img src="images/xxx.png"/>

        Args:
            content: 文档内容（Markdown 或 HTML）

        Returns:
            [(完整匹配, 图片路径), ...]
        """
        references = []

        # 匹配 Markdown 格式: ![alt](images/xxx.png)
        md_pattern = r'!\[([^\]]*)\]\((images/[^)]+)\)'
        for match in re.finditer(md_pattern, content):
            references.append((match.group(0), match.group(2)))

        # 匹配 HTML 格式: <img src="images/xxx.png"/>
        html_pattern = r'<img\s+[^>]*src="([^"]*images/[^"]*)"[^>]*/?>'
        for match in re.finditer(html_pattern, content):
            img_tag = match.group(0)
            img_path = match.group(1)
            # 避免重复添加
            if not any(ref[1] == img_path for ref in references):
                references.append((img_tag, img_path))

        logger.info(f"提取到 {len(references)} 个图片引用")
        return references

    def build_minio_key(self, parsed_minio_key: str, image_path: str) -> str:
        """
        构建图片的 MinIO 路径

        Args:
            parsed_minio_key: 解析后文件的 MinIO 路径
                              例: documents/{uuid}/parsed/xxx.md
            image_path: 图片相对路径
                        例: images/xxx.png

        Returns:
            图片的完整 MinIO 路径
            例: documents/{uuid}/parsed/images/xxx.png
        """
        # 获取 parsed 目录
        parsed_dir = parsed_minio_key.rsplit("/", 1)[0]
        # 拼接图片路径：parsed/images/xxx.png
        return f"{parsed_dir}/{image_path}"

    async def get_image_presigned_url(self, minio_key: str) -> str:
        """
        获取图片的预签名 URL

        Args:
            minio_key: 图片的 MinIO 路径

        Returns:
            预签名 URL
        """
        try:
            await self.minio_client.init()
            url = await self.minio_client.presigned_download_url(
                settings.MINIO_BUCKET,
                minio_key
            )
            return url
        except Exception as e:
            logger.error(f"获取预签名 URL 失败: {minio_key}, 错误: {e}")
            return None

    async def process_content(
        self,
        content: str,
        parsed_minio_key: str
    ) -> str:
        """
        处理文档内容：替换图片为文字描述（批量 + 限流）

        Args:
            content: 文档内容（Markdown/HTML）
            parsed_minio_key: 解析后文件的 MinIO 路径

        Returns:
            处理后的内容（图片已替换为文字）
        """
        import asyncio
        from config.settings import settings

        # 从配置读取并发参数
        max_concurrent = settings.VISION_MAX_CONCURRENT
        batch_size = settings.VISION_BATCH_SIZE

        # 1. 提取图片引用
        references = self.extract_image_references(content)
        if not references:
            logger.info("没有图片引用，跳过处理")
            return content

        # 2. 批量处理图片（限制并发）
        semaphore = asyncio.Semaphore(max_concurrent)
        processed_content = content

        async def process_single_image(idx, original_ref, image_path):
            """处理单张图片"""
            async with semaphore:
                logger.info(f"处理图片 [{idx}/{len(references)}]: {image_path}")

                # 构建 MinIO 路径
                minio_key = self.build_minio_key(parsed_minio_key, image_path)

                # 获取预签名 URL
                presigned_url = await self.get_image_presigned_url(minio_key)
                if not presigned_url:
                    logger.warning(f"无法获取图片 URL，跳过: {image_path}")
                    error_info = {
                        "image_path": image_path,
                        "error_type": "image_not_found",
                        "error_message": f"图片不存在或无法访问: {minio_key}",
                        "retry_count": 0,
                        "timestamp": datetime.now().isoformat()
                    }
                    return original_ref, None, error_info

                # 下载图片并调用视觉模型
                description = await self._describe_image_from_url(presigned_url)
                return original_ref, description, None

        # 分批处理
        all_errors = []
        for batch_start in range(0, len(references), batch_size):
            batch = references[batch_start:batch_start + batch_size]
            logger.info(f"处理批次 {batch_start // batch_size + 1}，共 {len(batch)} 张图片")

            # 并发处理当前批次（带重试）
            tasks = [
                self._process_with_retry(process_single_image, batch_start + i + 1, ref, path)
                for i, (ref, path) in enumerate(batch)
            ]
            results = await asyncio.gather(*tasks)

            # 替换图片为文字 + 收集错误
            try:
                for original_ref, description, error in results:
                    if description:
                        replacement = f"[图片内容]:\n{description}"
                        # 检查替换是否成功
                        if original_ref in processed_content:
                            processed_content = processed_content.replace(original_ref, replacement, 1)
                        else:
                            logger.warning(f"替换失败，原始引用不存在: {original_ref[:50]}...")
                    if error:
                        all_errors.append(error)
            except Exception as e:
                logger.error(f"处理结果时出错: {e}, results 类型: {type(results)}, 第一个结果: {results[0] if results else 'empty'}")
                raise

            logger.info(f"批次完成，已处理 {min(batch_start + batch_size, len(references))}/{len(references)}")

        # 统计实际替换数量
        remaining_references = self.extract_image_references(processed_content)
        replaced_count = len(references) - len(remaining_references)
        logger.info(f"内容处理完成：原始 {len(references)} 张，替换 {replaced_count} 张，剩余 {len(remaining_references)} 张，错误 {len(all_errors)} 个")
        return processed_content, all_errors

    async def _process_with_retry(self, func, *args, **kwargs):
        """
        带重试的图片处理

        Args:
            func: 要执行的异步函数

        Returns:
            (original_ref, description, error_info)
        """
        import asyncio
        from config.settings import settings

        max_retries = settings.VISION_MAX_RETRIES
        original_ref = args[1] if len(args) > 1 else None
        image_path = args[2] if len(args) > 2 else None

        for attempt in range(max_retries):
            try:
                result = await func(*args, **kwargs)
                # result = (original_ref, description, error)
                return result[0], result[1], result[2]
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避：1s, 2s, 4s
                    logger.warning(f"图片处理失败，{wait_time}秒后重试: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"图片处理失败，已达最大重试次数: {e}")
                    # 构建错误信息
                    error_info = {
                        "image_path": image_path,
                        "error_type": "vision_model_error",
                        "error_message": str(e),
                        "retry_count": max_retries,
                        "timestamp": datetime.now().isoformat()
                    }
                    # 返回原始引用，不替换，附带错误信息
                    return original_ref, None, error_info

    async def _describe_image_from_url(self, image_url: str) -> str:
        """
        从 URL 获取图片描述

        Args:
            image_url: 图片 URL

        Returns:
            图片描述
        """
        import httpx

        try:
            # 下载图片
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content
                logger.debug(f"图片下载成功: {len(image_data)} 字节")

            # 转为 base64
            import base64
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            # 调用视觉模型
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/chat",
                    json={
                        "model": settings.VISION_MODEL,
                        "messages": [
                            {
                                "role": "user",
                                "content": settings.VISION_PROMPT,
                                "images": [image_base64]
                            }
                        ],
                        "stream": False
                    }
                )
                if response.status_code != 200:
                    logger.error(f"视觉模型返回错误: {response.status_code} - {response.text[:200]}")
                    raise Exception(f"视觉模型错误: {response.status_code}")
                result = response.json()
                content = result.get("message", {}).get("content", "")
                if not content:
                    logger.error(f"视觉模型返回空内容: {result}")
                    raise Exception("视觉模型返回空内容")
                return content

        except Exception as e:
            logger.error(f"图片描述失败: {e}")
            raise  # 抛出异常，让上层记录错误


# 全局实例
image_processor = ImageProcessor()
