"""
OpenAI调用LLM基础封装
高可用优化：
    1. 重试策略：
        指数退避： 每次重试间隔翻倍
        最大重试次数: n
        可重试异常：超时，限流，网络错误
"""
import asyncio

from openai import AsyncOpenAI, OpenAIError, APITimeoutError, RateLimitError, APIError, APIConnectionError, AuthenticationError

from config.settings import settings
from config.logging import get_logger
from utils.cost_calculator import CalculateCostFactoriesService

logger = get_logger(__name__)

class LLMAPIService:
    """
    OpenAI 基础服务调用 LLM
    """
    def __init__(self, timeout=3000, temperature=0.3, top_p=0.3, top_k=20):
        self.client = AsyncOpenAI(
            api_key=settings.API_KEY,
            base_url=settings.BASE_URL,
            timeout=timeout
        )
        self.mode = settings.MODEL_NAME
        self.calculate_cost_service = CalculateCostFactoriesService(mode=self.mode)
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.stream_last_cost = 0

    def _build_message(self, messages, system_prompt):
        """
        公共方法，组装消息
        """
        all_messages = [
                {"role": "system", "content": system_prompt}
            ] 
        if messages:
            all_messages.extend(messages)
        return all_messages
    
    async def _retry_with_backoff(self, func, *args, **kwargs):
        """
        带重试的异步调用
        """
        last_exception = None
        # 遍历LLM最大重试次数
        for attempt in range(settings.LLM_MAX_RETRLES):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                # 判断是否是限流错误
                is_rate_limit = "429" in str(e) or "rate" in str(e).lower()
                if attempt < settings.LLM_MAX_RETRLES - 1:
                    # 如果是限流了，则等待时间应该要更长一些
                    if is_rate_limit:
                        delay = settings.LLM_RATE_LIMIT_DELAY * (2 ** attempt) # 5s 10s 20s
                        logger.warning(f"检测到限流错误，等待 {delay} 秒后重试，尝试: {attempt + 1} / {settings.LLM_MAX_RETRLES}： {e}")
                    else:
                        # 指数退避计算（避免雪崩，给服务器恢复时间）
                        delay = settings.LLM_RETRY_DELAY * (settings.LLM_RETRY_BACKOFF ** attempt)
                        logger.warning(f"调用失败：{delay}秒后重试， 尝试: {attempt + 1} / {settings.LLM_MAX_RETRLES}： {e}")
                    await asyncio.sleep(delay)
        logger.error(f"所有重试都失败了：{last_exception}")
        raise last_exception

    async def send_message(self, messages: list[dict], system_prompt: str = "你是一个资深的Python高级AI应用开发工程师"):
        """
        发送消息,非流式输出，返回完整JSON数据
        """
        all_messages = self._build_message(messages, system_prompt)
        cost = 0
        async def _call():
            # 调用 API 发送消息
            response = await self.client.chat.completions.create(
                model=self.mode,
                messages = all_messages,
                max_tokens=settings.MAX_COMPLETION_TOKENS,
                timeout=settings.LLM_TIMEOUT
            )
            if getattr(response, "usage") and response.usage:
                print("USAGE: ", response.usage)
                usage = response.usage
                input_token = usage.prompt_tokens              # ✅ 输入 token
                cache_input_token = usage.prompt_tokens_details.cached_tokens or 0  # ✅ 缓存命中
                completion_tokens = usage.completion_tokens    # ✅ 输出 token
                calculator = CalculateCostFactoriesService(mode=str(self.mode).split("-")[0])
                cost = calculator.calculate_cost(input_token, cache_input_token, completion_tokens)
            return {"content": response.choices[0].message.content, "cost": cost}
        try:
            return await self._retry_with_backoff(_call)
        except Exception as e:
            self._handle_error(e)
            raise

    async def send_message_streaming(self, messages: list[dict], system_prompt: str = "你是一个资深的Python高级AI应用开发工程师"):
        """
        流式输出，返回异步生成器
        """
        all_messages = self._build_message(messages, system_prompt)
        cost = 0
        async def _call():
            # 调用 API 发送消息
            response = await self.client.chat.completions.create(
                model=self.mode,
                messages=all_messages,
                stream=True,
                max_tokens=settings.MAX_COMPLETION_TOKENS,
                timeout=settings.LLM_TIMEOUT
            )
            return response
            
        try:
            # 尝试重建流
            response = await self._retry_with_backoff(_call)
            async for chunk in response:
                try:
                    # 计算成本
                    if chunk.usage:
                        # 输入token
                        input_token = chunk.usage.prompt_tokens
                        # 缓存token
                        cache_input_token = chunk.usage.prompt_tokens_details.cached_tokens if chunk.usage.prompt_tokens_details else 0
                        # 输出token
                        completion_tokens = chunk.usage.completion_tokens if chunk.usage.completion_tokens else 0
                        # 计算成本
                        calculator = CalculateCostFactoriesService(mode=str(self.mode).split("-")[0])
                        cost = calculator.calculate_cost(input_token, cache_input_token, completion_tokens)
                        print("cost: ", cost)
                    if chunk.choices:
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content
                except Exception as e:
                    # 如果是单个chunk解析失败了，允许跳过继续
                    continue
            # 测试流程结束后，更新总成本
            self.stream_last_cost = cost
        except Exception as e:
            self._handle_error(e)
            raise

    def _handle_error(self, e: Exception):
        """
        统一异常处理
        """
        if isinstance(e, APITimeoutError):
            raise ValueError("API调用超时")
        elif isinstance(e, RateLimitError):
            raise ValueError("API调用频率过高")
        elif isinstance(e, APIError):
            raise ValueError("API调用错误")
        elif isinstance(e, APIConnectionError):
            raise ValueError(f"API连接错误, 具体原因: {str(e)}")
        elif isinstance(e, AuthenticationError):
            raise ValueError(f"API认证错误, 具体原因: {str(e)}")
        else:
            raise ValueError(f"未知错误, 具体原因: {str(e)}")
        
