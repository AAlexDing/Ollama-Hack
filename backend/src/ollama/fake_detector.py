"""
伪装Ollama服务检测器
核心逻辑100%对齐Awesome-Ollama-Server实现
"""
from typing import Tuple

from src.logging import get_logger

logger = get_logger(__name__)


class FakeOllamaDetector:
    """
    伪装Ollama服务检测器
    
    对齐AOS实现:
    - ollama-utils.ts: isFakeOllama()
    - ollama-utils.ts: isValidTPS()
    - detect.ts: measureTPS() 的检测逻辑
    """

    # 伪装服务关键词列表（对齐AOS）
    # 对应 AOS: ollama-utils.ts:86-90
    FAKE_KEYWORDS = [
        "fake-ollama",
        "这是一条来自",
        "固定回复",
        # 扩展关键词
        "服务器繁忙",
        "测试回复",
        "test response",
    ]

    # TPS合理范围（对齐AOS）
    # 对应 AOS: ollama-utils.ts:79-80
    MIN_VALID_TPS = 0.01  # 最小有效 TPS
    MAX_VALID_TPS = 1000  # 最大有效 TPS

    @staticmethod
    def is_fake_response(text: str) -> bool:
        """
        检测响应内容是否包含伪装特征
        
        对应 AOS: ollama-utils.ts:86-90
        export function isFakeOllama(response: string): boolean {
          return response.includes('fake-ollama') || 
                 response.includes('这是一条来自') || 
                 response.includes('固定回复');
        }
        
        Args:
            text: 模型响应文本
            
        Returns:
            True: 检测到伪装特征
            False: 未检测到伪装特征
        """
        if not text:
            return False

        for keyword in FakeOllamaDetector.FAKE_KEYWORDS:
            if keyword in text:
                logger.warning(f"检测到伪装服务关键词: {keyword}")
                return True

        return False

    @staticmethod
    def is_valid_tps(tps: float) -> bool:
        """
        验证TPS是否在合理范围内
        
        对应 AOS: ollama-utils.ts:75-83
        export function isValidTPS(tps: number): boolean {
          const MIN_VALID_TPS = 0.01;
          const MAX_VALID_TPS = 1000;
          return tps >= MIN_VALID_TPS && tps <= MAX_VALID_TPS;
        }
        
        正常的 Ollama 服务 TPS 通常在:
        - 低端设备: 0.1 - 10 TPS
        - 中端设备: 10 - 50 TPS
        - 高端设备: 50 - 200 TPS
        - 超高性能: 200 - 300 TPS
        - 超过 1000 的值通常是异常的
        
        Args:
            tps: Tokens Per Second 值
            
        Returns:
            True: TPS在合理范围内
            False: TPS异常（可能是伪装服务）
        """
        is_valid = FakeOllamaDetector.MIN_VALID_TPS <= tps <= FakeOllamaDetector.MAX_VALID_TPS

        if not is_valid:
            logger.warning(
                f"检测到异常 TPS 值: {tps:.2f} "
                f"(合理范围: {FakeOllamaDetector.MIN_VALID_TPS}-{FakeOllamaDetector.MAX_VALID_TPS})"
            )

        return is_valid

    @staticmethod
    def detect(output: str, tps: float) -> Tuple[bool, str]:
        """
        综合检测服务是否为伪装
        
        对应 AOS: detect.ts:45-48, 56-60, 87-90
        
        检测维度:
        1. 响应内容特征匹配（关键词）
        2. TPS 数值合理性验证
        
        Args:
            output: 模型输出文本
            tps: 计算得到的 TPS 值
            
        Returns:
            (is_fake, reason): 
                - is_fake: True表示检测到伪装
                - reason: 检测到伪装的原因
        """
        # 1. 关键词检测
        if FakeOllamaDetector.is_fake_response(output):
            return True, "检测到伪装服务关键词"

        # 2. TPS合理性验证
        if not FakeOllamaDetector.is_valid_tps(tps):
            return (
                True,
                f"TPS异常: {tps:.2f} "
                f"(合理范围: {FakeOllamaDetector.MIN_VALID_TPS}-{FakeOllamaDetector.MAX_VALID_TPS})",
            )

        return False, ""


# 便捷函数（向后兼容）
def is_fake_ollama(response: str) -> bool:
    """
    便捷函数：检测是否为伪装服务
    保持与现有代码的兼容性
    """
    return FakeOllamaDetector.is_fake_response(response)

