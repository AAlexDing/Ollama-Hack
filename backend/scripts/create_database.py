"""
数据库初始化脚本
用于创建 ollama_hack 数据库（如果不存在）
"""
import asyncio

import aiomysql
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    host: str = "localhost"
    port: int = 3306
    username: str = "root"
    password: str = "19950526aA!"
    db: str = "ollama_hack"


async def create_database():
    """创建数据库（如果不存在）"""
    config = DatabaseConfig()
    
    print(f"正在连接到 MySQL 服务器 {config.host}:{config.port}...")
    
    # 连接到 MySQL 服务器（不指定数据库）
    try:
        conn = await aiomysql.connect(
            host=config.host,
            port=config.port,
            user=config.username,
            password=config.password,
            charset="utf8mb4",
        )
        
        cur = await conn.cursor()
        
        # 检查数据库是否存在
        await cur.execute("SHOW DATABASES LIKE %s", (config.db,))
        result = await cur.fetchone()
        
        if result:
            print(f"✅ 数据库 '{config.db}' 已存在，无需创建")
        else:
            # 创建数据库
            print(f"正在创建数据库 '{config.db}'...")
            await cur.execute(f"CREATE DATABASE IF NOT EXISTS `{config.db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            await conn.commit()
            print(f"✅ 数据库 '{config.db}' 创建成功！")
        
        cur.close()
        conn.close()
        
        print("\n数据库已准备就绪，可以启动应用了！")
        
    except Exception as e:
        print(f"❌ 创建数据库失败: {e}")
        print("\n请检查：")
        print(f"1. MySQL 服务器是否运行在 {config.host}:{config.port}")
        print(f"2. 用户名 '{config.username}' 和密码是否正确")
        print(f"3. 用户是否有创建数据库的权限")
        raise


if __name__ == "__main__":
    asyncio.run(create_database())

