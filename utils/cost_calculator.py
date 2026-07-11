"""
mimo-v2.5-pro
    输入（命中缓存）： 	¥0.025
    输入（未命中缓存）： 	¥3.00
    输出: ¥6.00
"""

from typing import Literal
from decimal import Decimal


class CalculateCostFactoriesService:
    """
    各大厂商模型成本计算工厂服务
    """
    def __init__(self, mode: Literal["mimo"]):
        self.mode = mode

    def __calculate_cost_for_mimo(self, input_token: int, cache_input_token: int, completion_tokens: int) -> Decimal:
        """
        通过输入token，输出token，和 输出token，计算mimo成本
        国内：元 / 百万 token
        """
        # 如果输入token或者输出token为0，直接返回0成本
        if input_token == 0 or completion_tokens == 0 or cache_input_token == 0:
            return Decimal("0.0000")

        input_token = input_token / 1000000
        cache_input_token = cache_input_token / 1000000
        completion_tokens = completion_tokens / 1000000
        no_cache_input_token = input_token - cache_input_token
        cache_input_price = Decimal(cache_input_token) * Decimal("0.025")
        no_cache_input_price = Decimal(no_cache_input_token) * Decimal("3.00")
        input_cost = cache_input_price + no_cache_input_price
        # 通过输出token，分别计算输出的成本
        completion_price = Decimal(completion_tokens) * Decimal("6.00")
        total_cost = input_cost + completion_price
        return Decimal(total_cost).quantize(Decimal('0.0001'))
    
    def calculate_cost(self, input_token: int, cache_input_token: int, completion_tokens: int):
        calculate_map = {
            "mimo": self.__calculate_cost_for_mimo
        }
        cost = calculate_map.get(self.mode.split("-")[0], lambda x, y, z: Decimal("0.0000"))
        return {
            "cost": float(cost(input_token, cache_input_token, completion_tokens)),
            "meta": {
                "input_token": input_token,
                "cache_input_token": cache_input_token,
                "completion_tokens": completion_tokens,
            }
        }

