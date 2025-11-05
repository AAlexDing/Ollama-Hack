import contextlib
from typing import Annotated, Any, AsyncIterator

import aiomysql
from fastapi import Depends
from sqlalchemy import TEXT
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declared_attr
from sqlmodel import SQLModel as _SQLModel

from .config import DatabaseEngine, LogLevels, get_config
from .logging import get_logger
from .utils import snake_case

config = get_config()
logger = get_logger(__name__)

LONGTEXT = TEXT
match config.database.engine:
    case DatabaseEngine.MYSQL:
        from sqlalchemy.dialects.mysql import LONGTEXT

        LONGTEXT = LONGTEXT


class SQLModel(_SQLModel):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return snake_case(cls.__name__)


class DatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, Any] | None = None):
        if engine_kwargs is None:
            engine_kwargs = {}

        self._engine = create_async_engine(host, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine)

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_engine_schema():
    match config.database.engine:
        case DatabaseEngine.MYSQL:
            schema = f"mysql+aiomysql://{config.database.username}:{config.database.password}@{config.database.host}:{config.database.port}/{config.database.db}?charset=utf8mb4"
        case _:
            raise ValueError(f"Unsupported database engine: {config.database.engine}")
    return schema


sessionmanager = DatabaseSessionManager(
    get_engine_schema(),
    {
        "echo": False,  # 关闭SQL语句日志输出
        "pool_size": 50,
        "max_overflow": 100,
        "pool_timeout": 60,
        "pool_recycle": 1800,
    },
)


async def ensure_database_exists():
    """确保数据库存在,如果不存在则创建"""
    match config.database.engine:
        case DatabaseEngine.MYSQL:
            try:
                # 连接到 MySQL 服务器（不指定数据库）
                conn = await aiomysql.connect(
                    host=config.database.host,
                    port=config.database.port,
                    user=config.database.username,
                    password=config.database.password,
                    charset="utf8mb4",
                )
                
                cur = await conn.cursor()
                
                # 检查数据库是否存在
                await cur.execute("SHOW DATABASES LIKE %s", (config.database.db,))
                result = await cur.fetchone()
                
                if result:
                    logger.info(f"数据库 '{config.database.db}' 已存在")
                else:
                    # 创建数据库
                    logger.info(f"正在创建数据库 '{config.database.db}'...")
                    await cur.execute(
                        f"CREATE DATABASE IF NOT EXISTS `{config.database.db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                    await conn.commit()
                    logger.info(f"数据库 '{config.database.db}' 创建成功！")
                
                await cur.close()
                conn.close()
                
            except Exception as e:
                logger.error(f"创建数据库失败: {e}")
                logger.error("请检查：")
                logger.error(f"1. MySQL 服务器是否运行在 {config.database.host}:{config.database.port}")
                logger.error(f"2. 用户名 '{config.database.username}' 和密码是否正确")
                logger.error(f"3. 用户是否有创建数据库的权限")
                raise
        case _:
            raise ValueError(f"不支持的数据库引擎: {config.database.engine}")


async def create_db_and_tables():
    async with sessionmanager.connect() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)


async def get_db_session():
    async with sessionmanager.session() as session:
        yield session


DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
