"""
视觉模型服务

支持 Ollama 和 OpenAI 两种 API 格式
通过 VISION_API_FORMAT 配置项切换：
- ollama: 使用 Ollama API 格式（本地部署）
- openai: 使用 OpenAI API 格式（硅基流动等云服务）
"""
import re
import os
import httpx
from typing import Optional
from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)


class VisionService:
    """视觉模型服务，支持 Ollama 和 OpenAI 双模式"""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.VISION_MODEL
        self.prompt = settings.VISION_PROMPT
        # API 格式：ollama 或 openai
        self.api_format = getattr(settings, "VISION_API_FORMAT", "ollama")

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

        # 根据 API 格式选择调用方式
        if self.api_format == "openai":
            return await self._call_openai_api(image_data, prompt)
        else:
            return await self._call_ollama_api(image_data, prompt)

    async def describe_image_from_base64(self, image_base64: str, prompt: str = None) -> str:
        """
        从 base64 描述图片

        Args:
            image_base64: 图片的 base64 编码
            prompt: 自定义提示词（可选）

        Returns:
            图片内容描述
        """
        prompt = prompt or self.prompt

        # 根据 API 格式选择调用方式
        if self.api_format == "openai":
            return await self._call_openai_api(image_base64, prompt)
        else:
            return await self._call_ollama_api(image_base64, prompt)

    def _compress_image_if_needed(self, image_data: str, max_size_mb: float = 1.0) -> str:
        """
        如果图片太大，压缩后返回新的 base64

        Args:
            image_data: 原始 base64 编码
            max_size_mb: 最大尺寸（MB）

        Returns:
            压缩后的 base64（或原始数据如果不需要压缩）
        """
        import base64
        from io import BytesIO

        # 计算当前大小
        current_size_mb = len(image_data) * 3 / 4 / (1024 * 1024)  # base64 大小约为原始的 4/3

        if current_size_mb <= max_size_mb:
            return image_data

        logger.info(f"图片过大 ({current_size_mb:.2f} MB)，正在压缩...")

        try:
            # 解码 base64
            image_bytes = base64.b64decode(image_data)

            # 打开图片
            from PIL import Image
            img = Image.open(BytesIO(image_bytes))

            # 计算缩放比例
            ratio = (max_size_mb / current_size_mb) ** 0.5
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)

            # 缩放
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 转回 base64
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            compressed_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

            new_size_mb = len(compressed_data) * 3 / 4 / (1024 * 1024)
            logger.info(f"图片压缩完成: {current_size_mb:.2f} MB -> {new_size_mb:.2f} MB")

            return compressed_data
        except Exception as e:
            logger.warning(f"图片压缩失败，使用原始数据: {e}")
            return image_data

    async def _call_ollama_api(self, image_data: str, prompt: str) -> str:
        """调用 Ollama API"""
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
                logger.info(f"图片描述成功（Ollama）: {image_data[:20]}...")
                return content
            except Exception as e:
                logger.error(f"图片描述失败（Ollama）: {e}")
                return f"[图片描述失败: {str(e)}]"

    async def _call_openai_api(self, image_data: str, prompt: str) -> str:
        """调用 OpenAI 兼容 API（硅基流动、智谱等）"""
        # 压缩图片（如果太大）
        image_data = self._compress_image_if_needed(image_data)

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.VISION_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": prompt
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_data}"
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 1024
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                logger.info(f"图片描述成功（OpenAI）: {image_data[:20]}...")
                return content
            except Exception as e:
                logger.error(f"图片描述失败（OpenAI）: {e}")
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
