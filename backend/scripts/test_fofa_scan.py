"""
FOFA扫描功能测试脚本
用于测试FOFA客户端和HTML解析器
"""
import asyncio

from src.fofa.client import FofaClient
from src.fofa.parser import FofaHTMLParser
from src.logging import get_logger

logger = get_logger(__name__)


async def test_fofa_client():
    """测试FOFA客户端"""
    logger.info("=" * 60)
    logger.info("开始测试FOFA客户端")
    logger.info("=" * 60)

    client = FofaClient(timeout=30)

    # 测试查询构建
    query1 = client.build_query(country="US")
    logger.info(f"默认查询: {query1}")

    query2 = client.build_query(country="CN", custom_query='app="Ollama" && city="Beijing"')
    logger.info(f"自定义查询: {query2}")

    # 测试Base64编码
    encoded = client.encode_query(query1)
    logger.info(f"编码后: {encoded}")

    # 测试实际搜索（可选，取消注释以测试）
    # logger.info("\n开始FOFA搜索（可能需要10-30秒）...")
    # try:
    #     html_content = await client.search(country="US")
    #     logger.info(f"响应大小: {len(html_content)} bytes")
    #     return html_content
    # except Exception as e:
    #     logger.error(f"搜索失败: {e}")
    #     return None


def test_html_parser():
    """测试HTML解析器"""
    logger.info("\n" + "=" * 60)
    logger.info("开始测试HTML解析器")
    logger.info("=" * 60)

    # 模拟FOFA返回的HTML片段
    mock_html = """
    <div class="hsxa-host"><a href="http://192.168.1.100:11434">192.168.1.100:11434</a></div>
    <div class="hsxa-host"><a href="https://example.com:11434">example.com:11434</a></div>
    <div class="hsxa-host"><a href="http://test.ollama.com">test.ollama.com</a></div>
    """

    parser = FofaHTMLParser()
    hosts = parser.extract_hosts(mock_html.encode("utf-8"))

    logger.info(f"解析到 {len(hosts)} 个主机:")
    for i, host in enumerate(hosts, 1):
        logger.info(f"  {i}. {host}")


async def main():
    """主函数"""
    logger.info("\n" + "=" * 60)
    logger.info("FOFA扫描功能测试")
    logger.info("=" * 60 + "\n")

    # 测试客户端
    html_content = await test_fofa_client()

    # 测试解析器
    test_html_parser()

    # 如果有实际的HTML内容，也测试一下
    if html_content:
        logger.info("\n" + "=" * 60)
        logger.info("解析实际FOFA响应")
        logger.info("=" * 60)
        parser = FofaHTMLParser()
        real_hosts = parser.extract_hosts(html_content)
        logger.info(f"从实际响应中解析到 {len(real_hosts)} 个主机")
        for i, host in enumerate(real_hosts[:10], 1):  # 只显示前10个
            logger.info(f"  {i}. {host}")
        if len(real_hosts) > 10:
            logger.info(f"  ... 还有 {len(real_hosts) - 10} 个主机")

    logger.info("\n" + "=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

