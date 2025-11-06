"""订阅API路由"""
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from src.database import DBSessionDep
from src.logging import get_logger
from src.user.models import UserDB
from src.user.service import get_current_admin_user

logger = get_logger(__name__)

from .schemas import (
    PullSubscriptionResponse,
    SubscriptionInfo,
    SubscriptionRequest,
    SubscriptionResponse,
    SubscriptionProgressResponse,
)
from .service import (
    create_subscription,
    get_subscription_info,
    get_subscription_progress,
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


@router.get("/{subscription_id}/progress", response_model=SubscriptionProgressResponse, summary="获取订阅进度")
async def get_subscription_progress_endpoint(
    subscription_id: int,
    session: DBSessionDep,
    current_user: UserDB = Depends(get_current_admin_user),
):
    """
    获取订阅进度（用于轮询）
    """
    return await get_subscription_progress(session, subscription_id)


@router.post("/{subscription_id}/pull", response_model=PullSubscriptionResponse, summary="手动拉取订阅")
async def pull_subscription_endpoint(
    subscription_id: int,
    background_task: BackgroundTasks,
    session: DBSessionDep,
    current_user: UserDB = Depends(get_current_admin_user),
    test_delay_seconds: int = 5,
):
    """
    手动触发订阅拉取（后台任务模式）

    - **test_delay_seconds**: 测试延迟秒数（默认5秒）
    """
    from src.subscription.models import SubscriptionDB, SubscriptionStatusEnum
    from sqlalchemy import select
    
    # 检查订阅是否存在
    result = await session.execute(select(SubscriptionDB).where(SubscriptionDB.id == subscription_id))
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found",
        )
    
    # 设置初始状态
    subscription.status = SubscriptionStatusEnum.IDLE
    subscription.progress_current = 0
    subscription.progress_total = 0
    subscription.progress_message = "准备开始拉取..."
    await session.commit()
    
    # 在后台执行拉取
    async def pull_in_background():
        from src.database import sessionmanager
        async with sessionmanager.session() as bg_session:
            try:
                from fastapi import BackgroundTasks
                bg_task = BackgroundTasks()
                await pull_subscription(bg_session, subscription_id, bg_task, test_delay_seconds)
            except Exception as e:
                logger.error(f"手动拉取订阅 {subscription_id} 失败: {e}", exc_info=True)
                # 确保失败时更新状态
                try:
                    sub = await bg_session.get(SubscriptionDB, subscription_id)
                    if sub:
                        sub.status = SubscriptionStatusEnum.FAILED
                        sub.progress_message = "手动拉取失败"
                        sub.error_message = str(e)
                        await bg_session.commit()
                except Exception as update_error:
                    logger.error(f"更新订阅状态失败: {update_error}")
    
    background_task.add_task(pull_in_background)
    
    return PullSubscriptionResponse(
        subscription_id=subscription_id,
        pull_count=0,
        created_count=0,
        message="拉取任务已启动，请查看进度",
    )


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

