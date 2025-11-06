"""
简化版订阅进度字段迁移
使用 SQLModel 自动创建/更新表结构
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import create_db_and_tables, ensure_database_exists


async def migrate():
    """执行数据库迁移"""
    print("正在连接数据库...")
    
    # 确保数据库存在
    await ensure_database_exists()
    print("✓ 数据库已就绪")
    
    # 创建/更新表结构
    print("\n正在更新表结构...")
    await create_db_and_tables()
    print("✓ 表结构已更新")
    
    print("\n✅ 迁移完成！")
    print("\n新字段已添加到 subscription 表:")
    print("  - status: 订阅状态")
    print("  - progress_current: 当前处理数量")
    print("  - progress_total: 总数量")
    print("  - progress_message: 进度消息")


if __name__ == "__main__":
    print("=" * 60)
    print("订阅进度字段迁移脚本")
    print("=" * 60)
    asyncio.run(migrate())

