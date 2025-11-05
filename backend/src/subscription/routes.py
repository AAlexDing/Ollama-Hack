"""订阅API路由"""
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends

from src.database import DBSessionDep
from src.user.models import UserDB
from src.user.service import get_current_admin_user

from .schemas import (
    PullSubscriptionResponse,
    SubscriptionInfo,
    SubscriptionRequest,
    SubscriptionResponse,
)
from .service import (
    create_subscription,
    get_subscription_info,
    list_subscriptions,
    pull_subscription,
    update_subscription,
)

router = APIRouter(prefix="/subscription", tags=["订阅"])


@router.post("/", response_model=SubscriptionResponse, summary="创建订阅")
async def create_subscription_endpoint(
    request: SubscriptionRequest,
    background_task: BackgroundTasks,
    session: DBSessionDep,
    current_user: UserDB = Depends(get_current_admin_user),
):
    """
    创建订阅配置（仅管理员）

    - **url**: 订阅地址URL
    - **pull_interval**: 拉取间隔（秒，60-86400）

    示例：
    ```json
    {
      "url": "https://awesome-ollama-server.vercel.app/data.json",
      "pull_interval": 300
    }
    ```
    """
    return await create_subscription(session, background_task, request, current_user.id)


@router.get("/{subscription_id}", response_model=SubscriptionInfo, summary="获取订阅信息")
async def get_subscription(
    subscription_id: int,
    session: DBSessionDep,
    current_user: UserDB = Depends(get_current_admin_user),
):
    """
    获取指定订阅的详细信息
    """
    return await get_subscription_info(session, subscription_id)


@router.get("/", response_model=List[SubscriptionInfo], summary="获取订阅列表")
async def list_subscriptions_endpoint(
    session: DBSessionDep,
    current_user: UserDB = Depends(get_current_admin_user),
    limit: int = 20,
    offset: int = 0,
):
    """
    获取订阅列表

    - **limit**: 返回数量限制（默认20）
    - **offset**: 偏移量（默认0）

    按创建时间倒序返回订阅记录
    """
    return await list_subscriptions(session, limit, offset)


@router.post("/{subscription_id}/pull", response_model=PullSubscriptionResponse, summary="手动拉取订阅")
async def pull_subscription_endpoint(
    subscription_id: int,
    background_task: BackgroundTasks,
    session: DBSessionDep,
    current_user: UserDB = Depends(get_current_admin_user),
    test_delay_seconds: int = 5,
):
    """
    手动触发订阅拉取

    - **test_delay_seconds**: 测试延迟秒数（默认5秒）
    """
    return await pull_subscription(session, subscription_id, background_task, test_delay_seconds)


@router.patch("/{subscription_id}", response_model=SubscriptionInfo, summary="更新订阅")
async def update_subscription_endpoint(
    subscription_id: int,
    session: DBSessionDep,
    current_user: UserDB = Depends(get_current_admin_user),
    pull_interval: Optional[int] = None,
    is_enabled: Optional[bool] = None,
):
    """
    更新订阅配置

    - **pull_interval**: 拉取间隔（秒，可选）
    - **is_enabled**: 是否启用（可选）
    """
    return await update_subscription(session, subscription_id, pull_interval, is_enabled)

