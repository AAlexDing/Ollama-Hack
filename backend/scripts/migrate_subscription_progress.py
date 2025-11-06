"""
订阅进度字段迁移脚本
为 subscription 表添加进度跟踪字段
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


async def migrate_subscription_progress():
    """添加订阅进度相关字段"""
    # 从环境变量读取配置
    host = os.getenv("DATABASE__HOST", "192.168.123.96")
    port = int(os.getenv("DATABASE__PORT", "3306"))
    username = os.getenv("DATABASE__USERNAME", "root")
    password = os.getenv("DATABASE__PASSWORD", "19950526aA!")
    db = os.getenv("DATABASE__DB", "ollama_hack")
    
    print(f"正在连接到数据库 {host}:{port}/{db}...")
    print(f"用户名: {username}")
    
    try:
        # 连接到数据库
        conn = await aiomysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            db=db,
            charset="utf8mb4",
        )
        
        cur = await conn.cursor()
        
        print("\n开始迁移...")
        
        # 检查字段是否已存在
        await cur.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'subscription' 
            AND COLUMN_NAME IN ('status', 'progress_current', 'progress_total', 'progress_message')
        """, (db,))
        existing_columns = [row[0] for row in await cur.fetchall()]
        
        if len(existing_columns) == 4:
            print("[INFO] 所有字段已存在，跳过迁移")
            await cur.close()
            conn.close()
            return
        
        # 添加 status 字段
        if 'status' not in existing_columns:
            print("添加 status 字段...")
            await cur.execute("""
                ALTER TABLE subscription 
                ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'idle' 
                COMMENT '订阅状态'
                AFTER error_message
            """)
            print("✓ status 字段添加成功")
        else:
            print("⊙ status 字段已存在")
        
        # 添加 progress_current 字段
        if 'progress_current' not in existing_columns:
            print("添加 progress_current 字段...")
            await cur.execute("""
                ALTER TABLE subscription 
                ADD COLUMN progress_current INT NOT NULL DEFAULT 0 
                COMMENT '当前处理数量'
                AFTER status
            """)
            print("✓ progress_current 字段添加成功")
        else:
            print("⊙ progress_current 字段已存在")
        
        # 添加 progress_total 字段
        if 'progress_total' not in existing_columns:
            print("添加 progress_total 字段...")
            await cur.execute("""
                ALTER TABLE subscription 
                ADD COLUMN progress_total INT NOT NULL DEFAULT 0 
                COMMENT '总数量'
                AFTER progress_current
            """)
            print("✓ progress_total 字段添加成功")
        else:
            print("⊙ progress_total 字段已存在")
        
        # 添加 progress_message 字段
        if 'progress_message' not in existing_columns:
            print("添加 progress_message 字段...")
            await cur.execute("""
                ALTER TABLE subscription 
                ADD COLUMN progress_message TEXT NULL 
                COMMENT '进度消息'
                AFTER progress_total
            """)
            print("✓ progress_message 字段添加成功")
        else:
            print("⊙ progress_message 字段已存在")
        
        # 提交更改
        await conn.commit()
        
        print("\n✅ 迁移完成！")
        print("\n新增字段:")
        print("  - status: VARCHAR(20) - 订阅状态 (idle/pulling/processing/completed/failed)")
        print("  - progress_current: INT - 当前处理数量")
        print("  - progress_total: INT - 总数量")
        print("  - progress_message: TEXT - 进度消息")
        
        # 验证表结构
        print("\n验证表结构...")
        await cur.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_DEFAULT, COLUMN_COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'subscription' 
            AND COLUMN_NAME IN ('status', 'progress_current', 'progress_total', 'progress_message')
            ORDER BY ORDINAL_POSITION
        """, (db,))
        
        columns = await cur.fetchall()
        print("\n当前字段信息:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]} (默认: {col[2]}, 注释: {col[3]})")
        
        await cur.close()
        conn.close()
        
        print("\n🎉 数据库迁移成功完成！")
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        print("\n请检查：")
        print(f"1. MySQL 服务器是否运行在 {host}:{port}")
        print(f"2. 数据库 '{db}' 是否存在")
        print(f"3. 用户 '{username}' 是否有 ALTER TABLE 权限")
        print(f"4. subscription 表是否存在")
        raise


if __name__ == "__main__":
    asyncio.run(migrate_subscription_progress())

