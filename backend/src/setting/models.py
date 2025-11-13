import datetime
from enum import Enum
from typing import Self

from pydantic import model_validator
from sqlalchemy import String
from sqlmodel import Column, Field

from src.database import SQLModel
from src.utils import now


class SystemSettingKey(str, Enum):
    UPDATE_ENDPOINT_TASK_INTERVAL_HOURS = "update_endpoint_task_interval_hours"
    DISABLE_OLLAMA_API_AUTH = "disable_ollama_api_auth"


class SystemSettings(SQLModel, table=True):
    key: SystemSettingKey = Field(
        primary_key=True,
        sa_type=String(50),  # 显式指定列长度为 50
    )
    value: str
    created_at: datetime.datetime = Field(default_factory=now, nullable=False)

    def validate_value(self) -> None:
        if self.key == SystemSettingKey.UPDATE_ENDPOINT_TASK_INTERVAL_HOURS:
            int_value = int(self.value)
            if int_value < 0:
                raise ValueError("Value must be greater or equal to 0")
            # if int_value > 24 * 60:
            #     raise ValueError("Value must be less than 24 * 60")
            self.value = str(int_value)
        elif self.key == SystemSettingKey.DISABLE_OLLAMA_API_AUTH:
            # 验证布尔值
            if self.value.lower() not in ("true", "false", "1", "0"):
                raise ValueError("Value must be 'true' or 'false'")
            # 标准化为 "true" 或 "false"
            self.value = "true" if self.value.lower() in ("true", "1") else "false"

    @model_validator(mode="after")
    def _validate_value(self) -> Self:
        self.validate_value()
        return self


DEFAULT_SETTINGS: dict[SystemSettingKey, str] = {
    SystemSettingKey.UPDATE_ENDPOINT_TASK_INTERVAL_HOURS: str(24),
    SystemSettingKey.DISABLE_OLLAMA_API_AUTH: "false",
}
