"""FOFA HTML解析器 - 核心逻辑对齐AOS实现"""
from typing import List

from src.logging import get_logger

logger = get_logger(__name__)


class FofaHTMLParser:
    """
    FOFA HTML 解析器
    核心解析逻辑与AOS的fofa-scan.mjs完全对齐
    """

    # 对应AOS: const HTML_START_TAG = 'hsxa-host"><a href="'
    HTML_START_TAG = 'hsxa-host"><a href="'
    # 对应AOS: const HTML_END_TAG = '"'
    HTML_END_TAG = '"'

    @staticmethod
    def extract_hosts(html_content: bytes) -> List[str]:
        """
        从HTML中提取主机地址
        对应AOS的while循环提取逻辑

        Args:
            html_content: FOFA返回的HTML内容

        Returns:
            主机地址列表
        """
        try:
            # 尝试UTF-8解码
            html_text = html_content.decode("utf-8")
        except UnicodeDecodeError:
            # 降级到GBK/GB2312
            try:
                html_text = html_content.decode("gbk", errors="ignore")
            except Exception:
                html_text = html_content.decode("gb2312", errors="ignore")

        hosts = []
        current_index = 0

        # 对应AOS: while (true) { ... }
        while True:
            # 对应AOS: const startPosition = responseText.indexOf(HTML_START_TAG, currentIndex)
            start_pos = html_text.find(FofaHTMLParser.HTML_START_TAG, current_index)
            if start_pos == -1:
                break

            # 对应AOS: startPosition + HTML_START_TAG.length
            start_pos += len(FofaHTMLParser.HTML_START_TAG)

            # 对应AOS: const endPosition = responseText.indexOf(HTML_END_TAG, startPosition + HTML_START_TAG.length)
            end_pos = html_text.find(FofaHTMLParser.HTML_END_TAG, start_pos)

            if end_pos == -1:
                break

            # 对应AOS: hosts.push(responseText.slice(startPosition + HTML_START_TAG.length, endPosition))
            host = html_text[start_pos:end_pos]

            # 只添加有效的HTTP/HTTPS URL
            if host and host.startswith("http"):
                hosts.append(host)

            # 对应AOS: currentIndex = endPosition
            current_index = end_pos

        logger.info(f"解析到 {len(hosts)} 个主机地址")
        return hosts

