from datetime import datetime, timedelta
from typing import Optional

from fastapi import BackgroundTasks, Depends, HTTPException, status
from fastapi_pagination import Page, Params, set_page
from fastapi_pagination.ext.sqlmodel import paginate as apaginate
from sqlalchemy import func, insert
from sqlalchemy.orm import selectinload
from sqlmodel import col, or_, select

from src.ai_model.models import (
    AIModelDB,
    AIModelPerformanceDB,
    AIModelStatusEnum,
    EndpointAIModelDB,
)
from src.database import DBSessionDep, sessionmanager
from src.logging import get_logger
from src.ollama.performance_test import EndpointTestResult, test_endpoint
from src.schema import SortOrder
from src.utils import now

from .models import (
    EndpointDB,
    EndpointTestTask,
)
from .schemas import (
    BatchOperationResult,
    EndpointAIModelInfo,
    EndpointBatchCreate,
    EndpointBatchOperation,
    EndpointCreateWithName,
    EndpointFilterParams,
    EndpointInfo,
    EndpointPerformanceInfo,
    EndpointUpdate,
    EndpointWithAIModelCount,
    EndpointWithAIModels,
    EndpointWithAIModelsRequest,
    TaskWithEndpoint,
)

logger = get_logger(__name__)


async def get_endpoint_by_id(session: DBSessionDep, endpoint_id: int) -> EndpointDB:
    """
    Get an endpoint by ID.
    """
    query = select(EndpointDB).options(selectinload(EndpointDB.performances))  # type: ignore

    query = query.where(EndpointDB.id == endpoint_id)

    result = await session.execute(query)
    endpoint = result.scalars().first()
    if endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")
    return endpoint


async def batch_create_or_update_endpoints(
    session: DBSessionDep,
    background_task: BackgroundTasks,
    endpoint_batch: EndpointBatchCreate,
) -> None:
    """
    Create or update multiple endpoints.
    """
    # 提取所有 URL
    urls = [ep.url for ep in endpoint_batch.endpoints]

    # 1. 查询已存在的 URL
    result = await session.execute(
        select(EndpointDB.url, EndpointDB.id).where(col(EndpointDB.url).in_(urls))
    )
    existing = {row[0]: row[1] for row in result.all()}

    # 2. 过滤出未存在的 URL
    new_urls = [url for url in urls if url not in existing]

    # 3. 批量插入新 URL
    new_ids = []
    if new_urls:
        # 构建插入数据
        new_urls = list(set(urls))
        to_insert = [{"url": url, "name": url} for url in new_urls]
        await session.execute(insert(EndpointDB).values(to_insert))
        await session.commit()

        # 查询新插入的记录的 ID
        result = await session.execute(
            select(EndpointDB.url, EndpointDB.id).where(col(EndpointDB.url).in_(new_urls))
        )
        new_ids = [row[1] for row in result.all()]

    # 4. 合并所有 ID
    all_ids = list(existing.values()) + new_ids

    # 使用调度器为每个端点创建测试任务
    async def create_test_tasks():
        from .scheduler import get_scheduler

        for eid in all_ids:
            scheduler = get_scheduler()
            await scheduler.schedule_endpoint_test(eid, now() + timedelta(seconds=5))

    background_task.add_task(create_test_tasks)


async def get_endpoint_by_url(session: DBSessionDep, url: str) -> EndpointDB:
    """
    Get an endpoint by URL.
    """
    result = await session.execute(select(EndpointDB).where(EndpointDB.url == url))
    endpoint = result.scalars().first()
    if endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")
    return endpoint


async def get_endpoints(
    session: DBSessionDep,
    params: EndpointFilterParams = Depends(),
) -> Page[EndpointDB]:
    """
    Get all endpoints with filtering, searching and sorting.

    params:
        - search: Optional search string for name or URL
        - order_by: Field to sort by
        - order: Sort order (asc or desc)
    """
    set_page(Page[EndpointDB])
    query = select(EndpointDB).options(selectinload(EndpointDB.performances))  # type: ignore

    # 添加搜索条件
    if params.search:
        search_term = f"%{params.search}%"
        query = query.where(
            or_(col(EndpointDB.name).ilike(search_term), col(EndpointDB.url).ilike(search_term))
        )

    # 添加排序
    if params.order_by:
        # 处理基本字段排序
        order_column = getattr(EndpointDB, params.order_by.value)
        if params.order == SortOrder.DESC:
            order_column = order_column.desc()
        query = query.order_by(order_column)

    if params.status:
        query = query.where(EndpointDB.status == params.status)

    return await apaginate(session, query, params)


async def create_or_update_endpoint(
    session: DBSessionDep,
    endpoint_create: EndpointCreateWithName,
) -> EndpointDB:
    """
    Create a new endpoint.
    """
    # Check if the endpoint already exists
    try:
        endpoint = await get_endpoint_by_url(session, endpoint_create.url)
    except HTTPException:
        endpoint = None
    if endpoint:
        # Update the endpoint
        endpoint_data = endpoint_create.model_dump()
        for key, value in endpoint_data.items():
            setattr(endpoint, key, value)
    else:
        # Create a new endpoint
        endpoint = EndpointDB(**endpoint_create.model_dump())
        session.add(endpoint)
    await session.commit()
    await session.refresh(endpoint)
    if endpoint.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate endpoint ID",
        )

    # 使用调度器创建测试任务
    await create_test_task(session, endpoint.id)

    return endpoint


async def update_endpoint(
    session: DBSessionDep,
    endpoint_id: int,
    endpoint_update: EndpointUpdate,
) -> EndpointDB:
    """
    Update an endpoint. Only admin or the owner can update it.
    """
    endpoint = await get_endpoint_by_id(session, endpoint_id)

    # Update fields
    update_data = endpoint_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(endpoint, key, value)

    await session.commit()
    await session.refresh(endpoint)
    return endpoint


async def delete_endpoint(
    session: DBSessionDep,
    endpoint_id: int,
) -> None:
    """
    Delete an endpoint. Only admin or the owner can delete it.
    """
    endpoint = await get_endpoint_by_id(session, endpoint_id)

    # 确保加载关联数据以激活级联删除
    await session.refresh(endpoint, ["ai_model_links", "performances"])

    logger.info(f"Deleting endpoint {endpoint.id} ({endpoint.name}) with all its relations")

    await session.delete(endpoint)
    await session.commit()
    logger.info(f"Endpoint {endpoint_id} deleted successfully")


async def get_ai_model_by_name_and_tag(
    session: DBSessionDep,
    name: str,
    tag: str,
) -> AIModelDB:
    """
    Get an AI model by name and tag.
    """
    result = await session.execute(
        select(AIModelDB).where(AIModelDB.name == name, AIModelDB.tag == tag)
    )
    ai_model = result.scalars().first()
    if ai_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI model not found")
    return ai_model


async def create_ai_model_if_not_exists(
    session: DBSessionDep,
    ai_model: AIModelDB,
) -> AIModelDB:
    """
    Create an AI model if it does not exist.
    """
    try:
        return await get_ai_model_by_name_and_tag(session, ai_model.name, ai_model.tag)
    except HTTPException:
        # If the AI model does not exist, create it
        pass

    session.add(ai_model)
    await session.commit()
    await session.refresh(ai_model)
    return ai_model


async def process_endpoint_test_result(
    session: DBSessionDep,
    endpoint_id: int,
    results: EndpointTestResult,
) -> None:
    """
    Process the endpoint test result.
    """
    if results.endpoint_performance:
        endpoint = await get_endpoint_by_id(session, endpoint_id)
        endpoint.status = results.endpoint_performance.status
        session.add(endpoint)
        results.endpoint_performance.endpoint_id = endpoint_id
        session.add(results.endpoint_performance)
        await session.commit()
        await session.refresh(results.endpoint_performance)


async def process_models_test_results(
    session: DBSessionDep,
    endpoint_id: int,
    results: EndpointTestResult,
) -> None:
    """
    Test all models of an endpoint and update their performance metrics.
    """
    performances = []
    new_links = []  # 只存储新创建的链接

    existing_associations = (
        select(EndpointAIModelDB)
        .where(EndpointAIModelDB.endpoint_id == endpoint_id)
        .options(
            selectinload(EndpointAIModelDB.ai_model),  # type: ignore
            selectinload(EndpointAIModelDB.performances),  # type: ignore
        )
    )
    existing_result = await session.execute(existing_associations)
    existing_link_map = {row.ai_model.id: row for row in existing_result.scalars().all()}

    mission_model_ids = list(existing_link_map.keys())
    for model_performance in results.model_performances:
        # 创建或获取模型
        model = await create_ai_model_if_not_exists(session, model_performance.ai_model)

        if model.id is None:
            continue

        try:
            performance = model_performance.performance
            if performance:
                performance.ai_model_id = model.id
                performance.endpoint_id = endpoint_id
                performances.append(performance)

            # 如果关系不存在且ID有效，则创建或获取关联表条目
            if model.id not in existing_link_map:
                # 再次查询数据库，确保记录不存在（处理并发情况）
                try:
                    link = await session.get(
                        EndpointAIModelDB,
                        (endpoint_id, model.id),
                    )
                    if link is None:
                        # 记录确实不存在，创建新链接
                        link = EndpointAIModelDB(endpoint_id=endpoint_id, ai_model_id=model.id)
                        existing_link_map[model.id] = link
                        new_links.append(link)  # 只将新链接添加到 new_links
                    else:
                        # 记录已存在（可能由并发任务创建），使用现有记录
                        await session.refresh(link)
                        existing_link_map[model.id] = link
                except Exception as e:
                    logger.debug(f"Error checking existing link: {e}")
                    # 如果查询失败，创建新链接（让数据库处理冲突）
                    link = EndpointAIModelDB(endpoint_id=endpoint_id, ai_model_id=model.id)
                    existing_link_map[model.id] = link
                    new_links.append(link)
            # 如果关系存在，则更新关联表条目
            else:
                link = existing_link_map[model.id]
                await session.refresh(link)

            # 添加性能数据
            if performance:
                link.performances.append(performance)
                link.status = performance.status
                link.token_per_second = performance.token_per_second
                if performance.connection_time is not None and link.max_connection_time is not None:
                    link.max_connection_time = max(
                        link.max_connection_time,
                        performance.connection_time,
                    )
                else:
                    link.max_connection_time = performance.connection_time

            if model.id in mission_model_ids:
                mission_model_ids.remove(model.id)
        except Exception as e:
            logger.error(
                f"Error processing model {model_performance.ai_model.name}:{model_performance.ai_model.tag}: {e}"
            )
            continue

    for model_id in mission_model_ids:
        link = existing_link_map[model_id]
        link.status = AIModelStatusEnum.MISSING
        # 注意：这些链接是已存在的，不需要添加到 session，只需要更新属性
        performance = AIModelPerformanceDB(
            endpoint_id=endpoint_id,
            ai_model_id=model_id,
            status=AIModelStatusEnum.MISSING,
        )
        performances.append(performance)

    # 批量添加新创建的链接和性能数据
    if new_links:
        # 处理可能的并发冲突
        links_to_add = []
        for link in new_links:
            try:
                # 再次检查是否已存在（处理并发情况）
                existing_link = await session.get(
                    EndpointAIModelDB,
                    (link.endpoint_id, link.ai_model_id),
                )
                if existing_link is None:
                    # 记录不存在，添加到待插入列表
                    links_to_add.append(link)
                else:
                    # 记录已存在（可能由并发任务创建），使用现有记录
                    await session.refresh(existing_link)
                    # 更新 existing_link_map，使用现有记录
                    existing_link_map[link.ai_model_id] = existing_link
            except Exception as e:
                logger.debug(f"Error checking link: {e}")
                # 如果检查失败，添加到待插入列表（让数据库处理冲突）
                links_to_add.append(link)
        
        # 批量添加剩余的新链接
        if links_to_add:
            try:
                session.add_all(links_to_add)
            except Exception as e:
                # 如果批量添加失败（可能是并发冲突），逐个添加
                logger.debug(f"Batch add failed, trying individual adds: {e}")
                for link in links_to_add:
                    try:
                        session.add(link)
                    except Exception:
                        # 如果添加失败（可能是并发冲突），忽略
                        logger.debug(f"Link already exists, skipping: {link.endpoint_id}-{link.ai_model_id}")
                        pass
    if performances:
        session.add_all(performances)


async def test_and_update_endpoint_and_models(
    endpoint_id: int,
) -> None:
    """
    Test an endpoint and update its performance metrics.
    """
    async with sessionmanager.session() as session:
        endpoint_query = select(EndpointDB).where(EndpointDB.id == endpoint_id)
        result = await session.execute(endpoint_query)
        endpoint = result.scalars().first()

        if endpoint is None:
            logger.error(f"Endpoint with ID {endpoint_id} not found")
            return None

    results = await test_endpoint(endpoint)

    async with sessionmanager.session() as session:
        await process_endpoint_test_result(session, endpoint_id, results)
        await process_models_test_results(session, endpoint_id, results)

        await session.commit()

        return


async def get_best_endpoints_for_model(
    session: DBSessionDep,
    model_id: int,
) -> list[EndpointDB]:
    """
    Get the best endpoint for a model.
    """
    query = (
        select(EndpointAIModelDB)
        .options(selectinload(EndpointAIModelDB.endpoint))  # type: ignore
        .where(
            EndpointAIModelDB.ai_model_id == model_id,
            EndpointAIModelDB.status == AIModelStatusEnum.AVAILABLE,
        )
    )
    query = query.order_by(col(EndpointAIModelDB.token_per_second).desc())
    result = await session.execute(query)
    links = result.scalars().all()
    if len(links) >= 10:
        links = links[:10]
    return [link.endpoint for link in links]


async def get_ai_model_links_by_endpoint_id(
    session: DBSessionDep,
    endpoint_id: int,
    params: Params = Depends(),
) -> Page[EndpointAIModelDB]:
    """
    Get all AI model links for an endpoint with pagination.
    """
    await get_endpoint_by_id(session, endpoint_id)

    set_page(Page[EndpointAIModelDB])

    # Base query to get AI models through the association table
    query = (
        select(EndpointAIModelDB)
        .options(
            selectinload(EndpointAIModelDB.ai_model),  # type: ignore
            selectinload(EndpointAIModelDB.performances),  # type: ignore
        )
        .where(EndpointAIModelDB.endpoint_id == endpoint_id)
    )

    return await apaginate(session, query, params)


async def get_endpoint_with_ai_models(
    session: DBSessionDep,
    request: EndpointWithAIModelsRequest = Depends(),
) -> EndpointWithAIModels:
    """
    Get an endpoint by ID with its associated AI models.
    """
    endpoint = await get_endpoint_by_id(session, request.endpoint_id)
    links = await get_ai_model_links_by_endpoint_id(session, request.endpoint_id, request)

    # Get recent performances
    recent_performances = endpoint.performances[:10] if endpoint.performances else []
    endpoint_performances = [
        EndpointPerformanceInfo(
            id=perf.id,
            status=perf.status,
            ollama_version=perf.ollama_version,
            created_at=perf.created_at,
        )
        for perf in recent_performances
    ]

    # Transform the AI models
    ai_models = []
    for link in links.items:
        if not link.ai_model:
            continue

        # Ensure ID is not None
        model_id = link.ai_model.id
        if model_id is None:
            continue

        ai_models.append(
            EndpointAIModelInfo(
                id=model_id,
                name=link.ai_model.name,
                tag=link.ai_model.tag,
                created_at=link.ai_model.created_at,
                status=link.status,
                token_per_second=link.token_per_second,
                max_connection_time=link.max_connection_time,
            )
        )

    # Create the response object
    return EndpointWithAIModels(
        id=endpoint.id,
        url=endpoint.url,
        name=endpoint.name,
        created_at=endpoint.created_at,
        status=endpoint.status,
        recent_performances=endpoint_performances,
        ai_models=Page(
            items=ai_models,
            total=links.total,
            page=links.page,
            size=links.size,
            pages=links.pages,
        ),
    )


async def get_endpoints_with_ai_model_counts(
    session: DBSessionDep, filter_params: EndpointFilterParams = Depends()
) -> Page[EndpointWithAIModelCount]:
    """
    Get all endpoints with AI model counts, with support for filtering, searching and sorting.
    """
    endpoints_page = await get_endpoints(session, filter_params)

    endpoints_with_counts = []

    for endpoint in endpoints_page.items:
        # Get the recent performances
        recent_performances = endpoint.performances[:1] if endpoint.performances else []
        endpoint_performances = [
            EndpointPerformanceInfo(
                id=perf.id,
                status=perf.status,
                ollama_version=perf.ollama_version,
                created_at=perf.created_at,
            )
            for perf in recent_performances
        ]

        # Count total AI models
        query = select(func.count()).where(EndpointAIModelDB.endpoint_id == endpoint.id)
        result = await session.execute(query)
        total_ai_model_count = result.scalar_one()

        # Count available AI models
        query = select(func.count()).where(
            EndpointAIModelDB.endpoint_id == endpoint.id,
            EndpointAIModelDB.status == AIModelStatusEnum.AVAILABLE,
        )
        result = await session.execute(query)
        avaliable_ai_model_count = result.scalar_one()

        query = (
            select(EndpointTestTask)
            .where(
                EndpointTestTask.endpoint_id == endpoint.id,
            )
            .order_by(col(EndpointTestTask.scheduled_at).desc())
        )
        result = await session.execute(query)
        task = result.scalars().first()
        task_status = task.status if task else None

        # Create the endpoint with counts
        endpoints_with_counts.append(
            EndpointWithAIModelCount(
                id=endpoint.id,
                url=endpoint.url,
                name=endpoint.name,
                created_at=endpoint.created_at,
                status=endpoint.status,
                recent_performances=endpoint_performances,
                total_ai_model_count=total_ai_model_count,
                avaliable_ai_model_count=avaliable_ai_model_count,
                task_status=task_status,
            )
        )

    # Return paginated results
    return Page(
        items=endpoints_with_counts,
        total=endpoints_page.total,
        page=endpoints_page.page,
        size=endpoints_page.size,
        pages=endpoints_page.pages,
    )


async def create_test_task(
    session: DBSessionDep,
    endpoint_id: int,
    scheduled_at: Optional[datetime] = None,
) -> Optional[EndpointTestTask]:
    """
    Create a new test task for an endpoint.
    """
    # Check if the endpoint exists
    await get_endpoint_by_id(session, endpoint_id)

    # Calculate the scheduled time if not provided
    if scheduled_at is None:
        scheduled_at = now() + timedelta(seconds=5)

    # Schedule the task with the scheduler
    from .scheduler import get_scheduler

    scheduler = get_scheduler()
    return await scheduler.schedule_endpoint_test(endpoint_id, scheduled_at)


async def get_task_by_id(
    session: DBSessionDep,
    task_id: int,
) -> EndpointTestTask:
    """
    Get a task by ID.
    """
    query = select(EndpointTestTask).where(EndpointTestTask.id == task_id)
    result = await session.execute(query)
    task = result.scalars().first()

    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return task


async def get_latest_task_for_endpoint(
    session: DBSessionDep,
    endpoint_id: int,
) -> EndpointTestTask:
    """
    Get the latest task for an endpoint.
    """
    query = select(EndpointTestTask).where(EndpointTestTask.endpoint_id == endpoint_id)
    query = query.order_by(col(EndpointTestTask.scheduled_at).desc())
    result = await session.execute(query)
    task = result.scalars().first()

    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return task


async def get_task_with_endpoint(
    session: DBSessionDep,
    task_id: int,
) -> TaskWithEndpoint:
    """
    Get a task by ID with its endpoint.
    """
    query = (
        select(EndpointTestTask)
        .options(selectinload(EndpointTestTask.endpoint))  # type: ignore
        .where(col(EndpointTestTask.id) == task_id)
    )
    result = await session.execute(query)
    task = result.scalars().first()

    if task is None or task.id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not found")

    return TaskWithEndpoint(
        id=task.id,
        endpoint_id=task.endpoint_id,
        status=task.status,
        scheduled_at=task.scheduled_at,
        last_tried=task.last_tried,
        created_at=task.created_at,
        endpoint=EndpointInfo(
            id=task.endpoint.id,
            url=task.endpoint.url,
            name=task.endpoint.name,
            created_at=task.endpoint.created_at,
            status=task.endpoint.status,
        ),
    )


async def manual_trigger_endpoint_test(
    session: DBSessionDep,
    endpoint_id: int,
) -> Optional[EndpointTestTask]:
    """
    Manually trigger a test for an endpoint.
    """
    # Check if the endpoint exists
    await get_endpoint_by_id(session, endpoint_id)

    # Create a task that will run immediately
    scheduled_at = now() + timedelta(seconds=2)
    return await create_test_task(session, endpoint_id, scheduled_at)


async def batch_test_endpoints(
    session: DBSessionDep,
    background_task: BackgroundTasks,
    batch_operation: EndpointBatchOperation,
) -> BatchOperationResult:
    """
    Batch test multiple endpoints.

    Args:
        session: Database session
        background_task: FastAPI background tasks
        batch_operation: The batch operation parameters

    Returns:
        BatchOperationResult with success and failure counts
    """
    success_count = 0
    failed_ids = {}

    # 创建一个后台任务来执行所有测试
    async def run_tests():
        from .scheduler import get_scheduler

        scheduler = get_scheduler()

        for endpoint_id in batch_operation.endpoint_ids:
            try:
                # 创建2秒后执行的测试任务
                scheduled_at = now() + timedelta(seconds=2)
                await scheduler.schedule_endpoint_test(endpoint_id, scheduled_at)
                logger.info(f"Scheduled test for endpoint {endpoint_id}")
            except Exception as e:
                logger.error(f"Failed to schedule test for endpoint {endpoint_id}: {e}")

    # 添加后台任务
    background_task.add_task(run_tests)

    # 统计成功和失败的数量
    for endpoint_id in batch_operation.endpoint_ids:
        try:
            # 验证端点是否存在
            await get_endpoint_by_id(session, endpoint_id)
            success_count += 1
        except Exception as e:
            failed_ids[str(endpoint_id)] = str(e)

    return BatchOperationResult(
        success_count=success_count,
        failed_count=len(batch_operation.endpoint_ids) - success_count,
        failed_ids=failed_ids,
    )


async def batch_delete_endpoints(
    session: DBSessionDep,
    batch_operation: EndpointBatchOperation,
) -> BatchOperationResult:
    """
    Batch delete multiple endpoints.

    Args:
        session: Database session
        batch_operation: The batch operation parameters

    Returns:
        BatchOperationResult with success and failure counts
    """
    success_count = 0
    failed_ids = {}

    for endpoint_id in batch_operation.endpoint_ids:
        try:
            # 获取并删除端点
            endpoint = await get_endpoint_by_id(session, endpoint_id)

            # 确保加载关联数据以激活级联删除
            await session.refresh(endpoint, ["ai_model_links", "performances"])

            logger.info(f"Deleting endpoint {endpoint.id} ({endpoint.name}) with all its relations")

            await session.delete(endpoint)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to delete endpoint {endpoint_id}: {e}")
            failed_ids[str(endpoint_id)] = str(e)

    # 提交所有更改
    await session.commit()

    return BatchOperationResult(
        success_count=success_count,
        failed_count=len(batch_operation.endpoint_ids) - success_count,
        failed_ids=failed_ids,
    )
