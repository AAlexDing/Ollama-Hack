"""FOFA API客户端 - 核心逻辑对齐AOS实现"""
import base64
from typing import Optional

import aiohttp

from src.logging import get_logger

logger = get_logger(__name__)


class FofaClient:
    """
    FOFA API 客户端
    核心逻辑与AOS的fofa-scan.mjs完全对齐
    """

    BASE_URL = "https://fofa.info/result"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def build_query(self, country: str = "US", custom_query: Optional[str] = None) -> str:
        """
        构建FOFA查询语句
        对应AOS: const searchQuery = `app="Ollama" && country="${country}"`
        """
        if custom_query:
            return custom_query
        return f'app="Ollama" && country="{country}"'

    def encode_query(self, query: str) -> str:
        """
        Base64编码查询
        对应AOS: Buffer.from(searchQuery).toString('base64')
        """
        return base64.b64encode(query.encode()).decode()

    async def search(self, country: str = "US", custom_query: Optional[str] = None) -> bytes:
        """
        执行FOFA搜索
        对应AOS: axios.get(baseUrl, { headers: { 'User-Agent': userAgent } })

        Args:
            country: 目标国家代码
            custom_query: 自定义查询语句

        Returns:
            HTML响应内容（bytes）

        Raises:
            Exception: 当FOFA API请求失败时
        """
        query = self.build_query(country, custom_query)
        encoded_query = self.encode_query(query)
        url = f"{self.BASE_URL}?qbase64={encoded_query}"

        logger.info(f"FOFA搜索: {query}")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url,
                    headers={"User-Agent": self.USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ssl=False,
                ) as response:
                    if response.status != 200:
                        raise Exception(f"FOFA API返回状态码: {response.status}")

                    content = await response.read()
                    logger.info(f"FOFA响应大小: {len(content)} bytes")
                    return content
            except aiohttp.ClientError as e:
                error_msg = f"请求失败: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg) from e
            except Exception as e:
                error_msg = f"未知错误: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg) from e

