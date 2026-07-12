"""
视觉模型服务

用于调用 Ollama 视觉模型（如 minicpm-v）分析图片内容
"""
import re
import os
import httpx
from typing import Optional
from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)


class VisionService:
    """视觉模型服务"""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.VISION_MODEL
        self.prompt = settings.VISION_PROMPT

    async def describe_image(self, image_path: str, prompt: str = None) -> str:
        """
        描述单张图片

        Args:
            image_path: 图片路径
            prompt: 自定义提示词（可选）

        Returns:
            图片内容描述
        """
        prompt = prompt or self.prompt

        # 读取图片并转为 base64
        import base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # 调用 Ollama API
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt,
                                "images": [image_data]
                            }
                        ],
                        "stream": False
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result.get("message", {}).get("content", "")
                logger.info(f"图片描述成功: {image_path}")
                return content
            except Exception as e:
                logger.error(f"图片描述失败: {image_path}, 错误: {e}")
                return f"[图片描述失败: {str(e)}]"

    async def replace_images_in_markdown(self, md_content: str, image_dir: str) -> str:
        """
        替换 Markdown 中的图片为文字描述

        Args:
            md_content: Markdown 内容
            image_dir: 图片目录路径

        Returns:
            替换后的 Markdown 内容
        """
        # 匹配 ![xxx](image.png) 格式
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'

        async def replace_match(match):
            alt_text = match.group(1)
            image_file = match.group(2)

            # 构建完整图片路径
            image_path = os.path.join(image_dir, image_file)

            # 检查图片是否存在
            if not os.path.exists(image_path):
                logger.warning(f"图片不存在: {image_path}")
                return match.group(0)

            # 获取图片描述
            description = await self.describe_image(image_path)

            # 返回替换后的内容
            return f"![{alt_text}]({image_file})\n\n[图片内容]:\n{description}"

        # 异步替换所有图片
        result = md_content
        matches = list(re.finditer(image_pattern, md_content))

        for match in matches:
            replacement = await replace_match(match)
            result = result.replace(match.group(0), replacement)

        logger.info(f"Markdown 图片替换完成，共处理 {len(matches)} 张图片")
        return result

    async def process_parsed_content(self, md_content: str, image_dir: str) -> str:
        """
        处理解析后的内容：替换图片为文字

        Args:
            md_content: MinerU 解析后的 Markdown
            image_dir: 图片目录

        Returns:
            处理后的 Markdown（图片已替换为文字）
        """
        # 检查是否有图片需要处理
        if not re.search(r'!\[([^\]]*)\]\(([^)]+)\)', md_content):
            logger.info("Markdown 中没有图片，跳过处理")
            return md_content

        # 替换图片为文字
        processed_content = await self.replace_images_in_markdown(md_content, image_dir)

        return processed_content


# 全局实例
vision_service = VisionService()
