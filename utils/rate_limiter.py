import time

from collections import defaultdict
from typing import Dict, Tuple


class TokenBucket:
    """
    令牌桶限流器
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity (int): 令牌桶的容量
            refill_rate (float): 令牌的填充速率（每秒填充的令牌数）
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens: Dict[str, Tuple[float, float]] = {}

    def _get_tokens(self, key: str) -> float:
        """
        获取当前令牌
        """
        now = time.time()
        if key not in self.tokens:
            self.tokens[key] = (self.capacity, now)
            return self.capacity
        tokens, last_refill = self.tokens[key]
        # 计算补充的令牌
        elapsed = now - last_refill
        tokens = min(self.capacity, tokens + elapsed * self.refill_rate)
        self.tokens[key] = (tokens, now)
        return tokens
    
    def acquire(self, key: str) -> bool:
        """
        尝试获取一个令牌
        """
        tokens = self._get_tokens(key)
        if tokens >= 1:
            self.tokens[key] = (tokens - 1, self.tokens[key][1])
            return True
        return False
    
    def get_wait_time(self, key: str) -> float:
        """
        获取等待时间
        """
        tokens = self._get_tokens(key)
        if tokens >= 1:
            return 0.0
        return (1 - tokens) / self.refill_rate  