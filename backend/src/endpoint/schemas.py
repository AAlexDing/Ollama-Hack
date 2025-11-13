from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi_pagination import Page, Params
from pydantic import BaseModel, field_validator

# Use the same StrEnum base class as in schema.py
from src.schema import FilterParams, StrEnum

from .models import EndpointStatusEnum, TaskStatus


class EndpointSortField(StrEnum):
    ID = "id"
    URL = "url"
    NAME = "name"
    CREATED_AT = "created_at"
    STATUS = "status"
    MAX_TPS = "max_tps"
    TPS_UPDATED_AT = "tps_updated_at"


class EndpointFilterParams(FilterParams[EndpointSortField]):
    status: Optional[EndpointStatusEnum] = None


class EndpointCreate(BaseModel):
    url: str

    @field_validator("url")
    def url_must_start_with_http(cls, v):
        if not v.startswith("http"):
            raise ValueError("URL must start with http:// or https://")
        return v


class EndpointCreateWithName(EndpointCreate):
    name: str = ""


class EndpointBatchCreate(BaseModel):
    endpoints: List[EndpointCreate]


class EndpointInfo(BaseModel):
    id: Optional[int] = None
    url: str
    name: str
    created_at: datetime
    status: EndpointStatusEnum

    class Config:
        from_attributes = True


class EndpointUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None


class EndpointPerformanceInfo(BaseModel):
    id: Optional[int] = None
    status: EndpointStatusEnum
    ollama_version: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EndpointWithPerformance(EndpointInfo):
    recent_performances: List[EndpointPerformanceInfo]


# New schemas for AI models associated with endpoints
class EndpointWithAIModelsRequest(Params):
    endpoint_id: int


class EndpointAIModelInfo(BaseModel):
    id: int
    name: str
    tag: str
    created_at: datetime
    status: str
    token_per_second: Optional[float] = None
    max_connection_time: Optional[float] = None

    class Config:
        from_attributes = True


class EndpointWithAIModels(EndpointWithPerformance):
    ai_models: Page[EndpointAIModelInfo]

    class Config:
        from_attributes = True


class EndpointAIModelSummary(BaseModel):
    """端点AI模型摘要信息（用于列表显示）"""
    name: str
    tag: str
    status: str  # 模型状态：available, unavailable, missing, fake等

    class Config:
        from_attributes = True


class EndpointWithAIModelCount(EndpointWithPerformance):
    total_ai_model_count: int
    avaliable_ai_model_count: int
    task_status: Optional[TaskStatus] = None
    max_tps: Optional[float] = None  # 最大TPS（所有可用模型的TPS最大值）
    tps_updated_at: Optional[datetime] = None  # TPS更新时间（最新性能测试时间）
    ai_models: List[EndpointAIModelSummary] = []  # AI模型列表（用于显示）

    class Config:
        from_attributes = True


class TaskInfo(BaseModel):
    id: int
    endpoint_id: int
    status: TaskStatus
    scheduled_at: datetime
    last_tried: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    endpoint_id: int
    scheduled_at: Optional[datetime] = None


class TaskWithEndpoint(TaskInfo):
    endpoint: EndpointInfo

    class Config:
        from_attributes = True


class EndpointBatchOperation(BaseModel):
    """Request model for batch operations on endpoints."""

    endpoint_ids: List[int]


class BatchOperationResult(BaseModel):
    """Response model for batch operations."""

    success_count: int
    failed_count: int
    failed_ids: Dict[str, Any] = {}  # Map of failed IDs to error messages

    class Config:
        from_attributes = True
