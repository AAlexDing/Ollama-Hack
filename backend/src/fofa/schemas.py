"""FOFA扫描请求/响应模型"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FofaScanRequest(BaseModel):
    """FOFA扫描请求"""

    country: str = Field(default="US", description="目标国家代码")
    custom_query: Optional[str] = Field(default=None, description="自定义查询语句")
    auto_test: bool = Field(default=True, description="是否自动触发检测")
    test_delay_seconds: int = Field(default=5, ge=0, le=300, description="检测延迟秒数")


class FofaScanHost(BaseModel):
    """扫描到的主机"""

    url: str
    created: bool  # 是否成功创建endpoint
    endpoint_id: Optional[int] = None
    error: Optional[str] = None


class FofaScanResponse(BaseModel):
    """FOFA扫描响应"""

    scan_id: int
    status: str
    query: str
    country: str
    total_found: int
    total_created: int
    message: str


class FofaScanInfo(BaseModel):
    """扫描记录信息"""

    id: int
    query: str
    country: str
    status: str
    total_found: int
    total_created: int
    created_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]

