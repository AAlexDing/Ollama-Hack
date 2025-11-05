"""
数据库初始化脚本（使用环境变量）
从环境变量读取数据库配置并创建数据库
"""
import asyncio
import os
import sys

# 设置输出编码为 UTF-8（Windows 兼容）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import aiomysql


async def create_database():
    """从环境变量读取配置并创建数据库"""
    # 从环境变量读取配置
    host = os.getenv("DATABASE__HOST", "192.168.123.96")
    port = int(os.getenv("DATABASE__PORT", "3306"))
    username = os.getenv("DATABASE__USERNAME", "root")
    password = os.getenv("DATABASE__PASSWORD", "19950526aA!")
    db = os.getenv("DATABASE__DB", "ollama_hack")
    
    print(f"正在连接到 MySQL 服务器 {host}:{port}...")
    print(f"用户名: {username}")
    print(f"目标数据库: {db}")
    
    # 连接到 MySQL 服务器（不指定数据库）
    try:
        conn = await aiomysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            charset="utf8mb4",
        )
        
        cur = await conn.cursor()
        
        # 检查数据库是否存在
        await cur.execute("SHOW DATABASES LIKE %s", (db,))
        result = await cur.fetchone()
        
        if result:
            print(f"[OK] 数据库 '{db}' 已存在，无需创建")
        else:
            # 创建数据库
            print(f"正在创建数据库 '{db}'...")
            await cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            await conn.commit()
            print(f"[OK] 数据库 '{db}' 创建成功！")
        
        await cur.close()
        conn.close()
        
        print("\n数据库已准备就绪，可以启动应用了！")
        
    except Exception as e:
        print(f"[ERROR] 创建数据库失败: {e}")
        print("\n请检查：")
        print(f"1. MySQL 服务器是否运行在 {host}:{port}")
        print(f"2. 用户名 '{username}' 和密码是否正确")
        print(f"3. 用户是否有创建数据库的权限")
        raise


if __name__ == "__main__":
    asyncio.run(create_database())

