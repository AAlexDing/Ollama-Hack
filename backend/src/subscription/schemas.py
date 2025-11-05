"""订阅请求/响应模型"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class SubscriptionItem(BaseModel):
    """订阅数据项（从JSON解析）"""

    server: str = Field(description="服务器地址")
    models: List[str] = Field(description="模型列表")
    tps: float = Field(default=0.0, description="TPS值")
    lastUpdate: str = Field(description="最后更新时间")
    status: str = Field(description="状态")


class SubscriptionRequest(BaseModel):
    """订阅配置请求"""

    url: HttpUrl = Field(description="订阅地址URL")
    pull_interval: int = Field(default=300, ge=60, le=86400, description="拉取间隔（秒，60-86400）")


class SubscriptionResponse(BaseModel):
    """订阅响应"""

    subscription_id: int
    url: str
    pull_interval: int
    message: str


class SubscriptionInfo(BaseModel):
    """订阅信息"""

    id: int
    url: str
    pull_interval: int
    last_pull_at: Optional[datetime]
    last_pull_count: int
    total_pulls: int
    total_created: int
    is_enabled: bool
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


class PullSubscriptionResponse(BaseModel):
    """拉取订阅响应"""

    subscription_id: int
    pull_count: int
    created_count: int
    message: str

