"""订阅数据库模型"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, Enum as SQLEnum
from sqlmodel import Field

from src.database import SQLModel
from src.utils import now


class SubscriptionStatusEnum(str, Enum):
    """订阅状态枚举"""
    IDLE = "idle"              # 空闲状态
    PULLING = "pulling"        # 正在拉取数据
    PROCESSING = "processing"  # 正在处理数据
    COMPLETED = "completed"    # 完成
    FAILED = "failed"          # 失败


class SubscriptionDB(SQLModel, table=True):
    """订阅配置表"""

    __tablename__ = "subscription"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(index=True, description="订阅地址URL")
    pull_interval: int = Field(default=300, description="拉取间隔（秒）")
    last_pull_at: Optional[datetime] = Field(default=None, description="上次拉取时间")
    last_pull_count: int = Field(default=0, description="上次拉取数量")
    total_pulls: int = Field(default=0, description="总拉取次数")
    total_created: int = Field(default=0, description="总创建端点数量")
    is_enabled: bool = Field(default=True, description="是否启用")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    status: SubscriptionStatusEnum = Field(
        default=SubscriptionStatusEnum.IDLE,
        description="订阅状态",
        sa_column=Column(
            SQLEnum(SubscriptionStatusEnum, values_callable=lambda x: [e.value for e in x]),
            nullable=False,
            default="idle"
        )
    )
    progress_current: int = Field(default=0, description="当前处理数量")
    progress_total: int = Field(default=0, description="总数量")
    progress_message: Optional[str] = Field(default=None, description="进度消息")
    created_at: datetime = Field(default_factory=now, description="创建时间")
    updated_at: datetime = Field(default_factory=now, description="更新时间")
    created_by: Optional[int] = Field(foreign_key="user.id", default=None, description="创建者ID")


class SubscriptionPullHistoryDB(SQLModel, table=True):
    """订阅拉取历史表"""

    __tablename__ = "subscription_pull_history"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    subscription_id: int = Field(foreign_key="subscription.id", index=True, description="订阅ID")
    pull_count: int = Field(default=0, description="本次拉取数量")
    created_count: int = Field(default=0, description="本次创建端点数量")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    pulled_at: datetime = Field(default_factory=now, description="拉取时间")

