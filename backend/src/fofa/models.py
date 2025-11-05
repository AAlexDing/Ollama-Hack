"""FOFA扫描数据库模型"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field

from src.database import SQLModel
from src.utils import now


class FofaScanStatus(str, Enum):
    """FOFA扫描状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FofaScanDB(SQLModel, table=True):
    """FOFA扫描记录表"""

    __tablename__ = "fofa_scan"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    query: str = Field(index=True, description="搜索查询语句")
    country: str = Field(index=True, description="目标国家代码")
    status: FofaScanStatus = Field(default=FofaScanStatus.PENDING, description="扫描状态")
    total_found: int = Field(default=0, description="发现的主机数量")
    total_created: int = Field(default=0, description="成功创建的端点数量")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    created_at: datetime = Field(default_factory=now, description="创建时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")
    created_by: Optional[int] = Field(foreign_key="user.id", default=None, description="创建者ID")

