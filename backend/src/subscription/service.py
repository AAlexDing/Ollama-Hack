"""订阅业务逻辑层"""
import aiohttp
import asyncio
import json
import ssl
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import BackgroundTasks, HTTPException, status
from sqlmodel import col, select

from src.database import DBSessionDep, sessionmanager
from src.endpoint.models import EndpointDB
from src.endpoint.service import create_test_task
from src.logging import get_logger
from src.utils import now

from .models import SubscriptionDB, SubscriptionPullHistoryDB
from .schemas import (
    PullSubscriptionResponse,
    SubscriptionInfo,
    SubscriptionItem,
    SubscriptionRequest,
    SubscriptionResponse,
)

logger = get_logger(__name__)


async def create_or_get_subscription(
    session: DBSessionDep, request: SubscriptionRequest, user_id: Optional[int] = None
) -> SubscriptionDB:
    """
    创建或获取订阅配置

    Args:
        session: 数据库会话
        request: 订阅请求
        user_id: 创建者ID

    Returns:
        订阅配置
    """
    # 检查是否已存在相同URL的订阅
    query = select(SubscriptionDB).where(SubscriptionDB.url == str(request.url))
    result = await session.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        # 更新现有订阅
        existing.pull_interval = request.pull_interval
        existing.updated_at = now()
        await session.commit()
        await session.refresh(existing)
        return existing

    # 创建新订阅
    subscription = SubscriptionDB(
        url=str(request.url),
        pull_interval=request.pull_interval,
        created_by=user_id,
    )
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return subscription


async def pull_subscription(
    session: DBSessionDep,
    subscription_id: int,
    background_task: BackgroundTasks,
    test_delay_seconds: int = 5,
) -> PullSubscriptionResponse:
    """
    拉取订阅数据并创建端点

    Args:
        session: 数据库会话
        subscription_id: 订阅ID
        background_task: 后台任务
        test_delay_seconds: 测试延迟秒数

    Returns:
        拉取结果
    """
    # 获取订阅配置
    query = select(SubscriptionDB).where(SubscriptionDB.id == subscription_id)
    result = await session.execute(query)
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found",
        )

    if not subscription.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subscription {subscription_id} is disabled",
        )

    try:
        # 拉取JSON数据
        # 先尝试正常SSL连接，失败时降级到不验证SSL（用于处理自签名证书等情况）
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        data = None
        last_error = None

        # 第一次尝试：正常SSL验证
        try:
            async with aiohttp.ClientSession(timeout=timeout) as http_session:
                async with http_session.get(subscription.url, allow_redirects=True) as response:
                    if response.status != 200:
                        error_detail = f"HTTP {response.status}: {response.reason}"
                        try:
                            error_text = await response.text()
                            if error_text:
                                error_detail = f"{error_detail} - {error_text[:200]}"
                        except Exception:
                            pass
                        raise HTTPException(
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Failed to fetch subscription: {error_detail}",
                        )
                    data = await response.json()
                    logger.debug(f"订阅拉取成功（正常SSL）: {subscription.url}")
        except (aiohttp.ClientError, asyncio.TimeoutError, HTTPException) as e:
            # 如果是HTTPException（非200状态码），直接抛出
            if isinstance(e, HTTPException):
                raise
            last_error = e
            logger.warning(
                f"订阅拉取正常SSL连接失败: {subscription.url}, "
                f"错误: {str(e)}, 尝试不验证SSL..."
            )

            # 第二次尝试：不验证SSL（用于处理自签名证书等情况）
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                connector = aiohttp.TCPConnector(ssl=ssl_context, limit=10)

                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as http_session:
                    async with http_session.get(subscription.url, allow_redirects=True) as response:
                        if response.status != 200:
                            error_detail = f"HTTP {response.status}: {response.reason}"
                            try:
                                error_text = await response.text()
                                if error_text:
                                    error_detail = f"{error_detail} - {error_text[:200]}"
                            except Exception:
                                pass
                            raise HTTPException(
                                status_code=status.HTTP_502_BAD_GATEWAY,
                                detail=f"Failed to fetch subscription: {error_detail}",
                            )
                        data = await response.json()
                        logger.debug(f"订阅拉取成功（不验证SSL）: {subscription.url}")
            except aiohttp.ClientError as e2:
                error_msg = f"Connection error: {str(e2)} (tried both SSL verified and unverified)"
                logger.error(f"订阅拉取连接错误: {subscription.url}, {error_msg}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=error_msg,
                )
            except asyncio.TimeoutError:
                error_msg = "Connection timeout (30s)"
                logger.error(f"订阅拉取超时: {subscription.url}")
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=error_msg,
                )

        if data is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to fetch subscription data: {str(last_error)}",
            )

        # 解析JSON数据
        items: List[SubscriptionItem] = [SubscriptionItem(**item) for item in data]

        # 1. 提取并验证所有服务器URL，去重
        valid_urls = []
        for item in items:
            # 验证服务器地址格式
            if not item.server.startswith(("http://", "https://")):
                logger.warning(f"Invalid server URL format: {item.server}")
                continue
            valid_urls.append(item.server)
        
        # 去重（在订阅数据中可能有重复的URL）
        valid_urls = list(set(valid_urls))
        
        if not valid_urls:
            logger.warning("订阅拉取的数据中没有有效的服务器URL")
            return PullSubscriptionResponse(
                subscription_id=subscription_id,
                pull_count=len(items),
                created_count=0,
                message="拉取的数据中没有有效的服务器URL",
            )

        # 2. 批量查询数据库中已存在的URL
        result = await session.execute(
            select(EndpointDB.url, EndpointDB.id).where(col(EndpointDB.url).in_(valid_urls))
        )
        existing_urls_map = {row[0]: row[1] for row in result.all()}
        
        # 3. 过滤出需要创建的URL（数据库中不存在的）
        new_urls = [url for url in valid_urls if url not in existing_urls_map]
        
        # 4. 批量创建新端点
        created_count = 0
        new_endpoint_ids = []
        if new_urls:
            from sqlalchemy import insert
            
            # 批量插入新端点
            to_insert = [{"url": url, "name": url} for url in new_urls]
            await session.execute(insert(EndpointDB).values(to_insert))
            await session.commit()
            
            # 查询新插入的端点ID
            result = await session.execute(
                select(EndpointDB.url, EndpointDB.id).where(col(EndpointDB.url).in_(new_urls))
            )
            new_endpoint_ids = [row[1] for row in result.all() if row[1] is not None]
            created_count = len(new_endpoint_ids)
        
        # 5. 合并所有端点ID（已存在的 + 新创建的）
        all_endpoint_ids = list(existing_urls_map.values()) + new_endpoint_ids
        
        # 6. 为所有端点创建测试任务（延迟或立即）
        if all_endpoint_ids:
            if test_delay_seconds > 0:
                from src.endpoint.scheduler import get_scheduler
                
                scheduler = get_scheduler()
                for endpoint_id in all_endpoint_ids:
                    if endpoint_id:
                        await scheduler.schedule_endpoint_test(
                            endpoint_id, now() + timedelta(seconds=test_delay_seconds)
                        )
            else:
                for endpoint_id in all_endpoint_ids:
                    if endpoint_id:
                        await create_test_task(session, endpoint_id)

        # 更新订阅记录
        subscription.last_pull_at = now()
        subscription.last_pull_count = len(items)
        subscription.total_pulls += 1
        subscription.total_created += created_count
        subscription.error_message = None
        subscription.updated_at = now()
        await session.commit()

        # 创建拉取历史记录
        history = SubscriptionPullHistoryDB(
            subscription_id=subscription_id,
            pull_count=len(items),
            created_count=created_count,
        )
        session.add(history)
        await session.commit()

        logger.info(
            f"订阅拉取完成: {subscription.url}, "
            f"拉取 {len(items)} 个, 创建 {created_count} 个端点"
        )

        return PullSubscriptionResponse(
            subscription_id=subscription_id,
            pull_count=len(items),
            created_count=created_count,
            message=f"成功拉取 {len(items)} 个服务器，创建 {created_count} 个端点",
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"订阅拉取失败: {subscription.url}, 错误: {error_msg}")

        # 更新错误信息（重新获取 subscription 对象，避免访问过期属性）
        try:
            # 尝试回滚之前的操作
            await session.rollback()
            # 重新获取 subscription 对象
            subscription = await session.get(SubscriptionDB, subscription_id)
            if subscription:
                subscription.error_message = error_msg
                subscription.updated_at = now()
                await session.commit()
        except Exception as update_error:
            logger.error(f"更新订阅错误信息失败: {update_error}")
            # 如果更新失败，继续抛出原始异常

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pull subscription: {error_msg}",
        )


async def create_subscription(
    session: DBSessionDep,
    background_task: BackgroundTasks,
    request: SubscriptionRequest,
    user_id: Optional[int] = None,
) -> SubscriptionResponse:
    """
    创建订阅配置

    Args:
        session: 数据库会话
        background_task: 后台任务
        request: 订阅请求
        user_id: 创建者ID

    Returns:
        订阅响应
    """
    subscription = await create_or_get_subscription(session, request, user_id)

    # 创建后台任务函数来执行首次拉取
    async def pull_subscription_background(subscription_id: int):
        """后台执行订阅拉取"""
        async with sessionmanager.session() as bg_session:
            try:
                # 创建临时BackgroundTasks实例（实际不需要，pull_subscription内部不使用它）
                from fastapi import BackgroundTasks
                bg_task = BackgroundTasks()
                await pull_subscription(bg_session, subscription_id, bg_task, test_delay_seconds=5)
                logger.info(f"订阅 {subscription_id} 首次拉取完成")
            except Exception as e:
                logger.error(f"订阅 {subscription_id} 首次拉取失败: {e}", exc_info=True)

    # 在后台执行首次拉取，不阻塞响应
    if subscription.id:
        background_task.add_task(pull_subscription_background, subscription.id)
        message = "订阅已创建，首次拉取正在后台执行"
    else:
        message = "订阅已创建，但无法执行首次拉取（订阅ID为空）"

    return SubscriptionResponse(
        subscription_id=subscription.id if subscription.id else 0,
        url=subscription.url,
        pull_interval=subscription.pull_interval,
        message=message,
    )


async def get_subscription_info(session: DBSessionDep, subscription_id: int) -> SubscriptionInfo:
    """
    获取订阅信息

    Args:
        session: 数据库会话
        subscription_id: 订阅ID

    Returns:
        订阅信息
    """
    query = select(SubscriptionDB).where(SubscriptionDB.id == subscription_id)
    result = await session.execute(query)
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found",
        )

    return SubscriptionInfo(
        id=subscription.id if subscription.id else 0,
        url=subscription.url,
        pull_interval=subscription.pull_interval,
        last_pull_at=subscription.last_pull_at,
        last_pull_count=subscription.last_pull_count,
        total_pulls=subscription.total_pulls,
        total_created=subscription.total_created,
        is_enabled=subscription.is_enabled,
        error_message=subscription.error_message,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
    )


async def list_subscriptions(session: DBSessionDep, limit: int = 20, offset: int = 0) -> List[SubscriptionInfo]:
    """
    获取订阅列表

    Args:
        session: 数据库会话
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        订阅列表
    """
    query = select(SubscriptionDB).order_by(SubscriptionDB.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    subscriptions = result.scalars().all()

    return [
        SubscriptionInfo(
            id=sub.id if sub.id else 0,
            url=sub.url,
            pull_interval=sub.pull_interval,
            last_pull_at=sub.last_pull_at,
            last_pull_count=sub.last_pull_count,
            total_pulls=sub.total_pulls,
            total_created=sub.total_created,
            is_enabled=sub.is_enabled,
            error_message=sub.error_message,
            created_at=sub.created_at,
            updated_at=sub.updated_at,
        )
        for sub in subscriptions
    ]


async def update_subscription(
    session: DBSessionDep,
    subscription_id: int,
    pull_interval: Optional[int] = None,
    is_enabled: Optional[bool] = None,
) -> SubscriptionInfo:
    """
    更新订阅配置

    Args:
        session: 数据库会话
        subscription_id: 订阅ID
        pull_interval: 拉取间隔（可选）
        is_enabled: 是否启用（可选）

    Returns:
        更新后的订阅信息
    """
    query = select(SubscriptionDB).where(SubscriptionDB.id == subscription_id)
    result = await session.execute(query)
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription {subscription_id} not found",
        )

    if pull_interval is not None:
        subscription.pull_interval = pull_interval
    if is_enabled is not None:
        subscription.is_enabled = is_enabled

    subscription.updated_at = now()
    await session.commit()
    await session.refresh(subscription)

    return SubscriptionInfo(
        id=subscription.id if subscription.id else 0,
        url=subscription.url,
        pull_interval=subscription.pull_interval,
        last_pull_at=subscription.last_pull_at,
        last_pull_count=subscription.last_pull_count,
        total_pulls=subscription.total_pulls,
        total_created=subscription.total_created,
        is_enabled=subscription.is_enabled,
        error_message=subscription.error_message,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
    )

