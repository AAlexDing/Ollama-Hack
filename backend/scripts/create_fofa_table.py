"""创建FOFA扫描表"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from src.database import create_db_and_tables
from src.logging import get_logger

logger = get_logger(__name__)


async def main():
    logger.info("开始创建数据库表...")
    await create_db_and_tables()
    logger.info("数据库表创建完成（包括FOFA扫描表）")


if __name__ == "__main__":
    asyncio.run(main())

