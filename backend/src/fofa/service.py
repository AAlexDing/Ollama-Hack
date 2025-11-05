"""FOFA扫描业务逻辑层"""
from datetime import timedelta
from typing import List, Optional

from fastapi import BackgroundTasks, HTTPException, status
from sqlmodel import select

from src.database import DBSessionDep, sessionmanager
from src.endpoint.schemas import EndpointCreateWithName
from src.endpoint.service import create_or_update_endpoint, create_test_task
from src.logging import get_logger
from src.utils import now

from .client import FofaClient
from .models import FofaScanDB, FofaScanStatus
from .parser import FofaHTMLParser
from .schemas import FofaScanInfo, FofaScanRequest, FofaScanResponse

logger = get_logger(__name__)


async def create_scan_record(
    session: DBSessionDep, request: FofaScanRequest, user_id: Optional[int] = None
) -> FofaScanDB:
    """
    创建扫描记录

    Args:
        session: 数据库会话
        request: 扫描请求
        user_id: 创建者ID

    Returns:
        创建的扫描记录
    """
    client = FofaClient()
    query = client.build_query(request.country, request.custom_query)

    scan = FofaScanDB(query=query, country=request.country, status=FofaScanStatus.PENDING, created_by=user_id)
    session.add(scan)
    await session.commit()
    await session.refresh(scan)
    return scan


async def execute_fofa_scan(
    session: DBSessionDep,
    background_task: BackgroundTasks,
    request: FofaScanRequest,
    user_id: Optional[int] = None,
) -> FofaScanResponse:
    """
    执行FOFA扫描

    Args:
        session: 数据库会话
        background_task: 后台任务
        request: 扫描请求
        user_id: 创建者ID

    Returns:
        扫描响应
    """
    # 1. 创建扫描记录
    scan = await create_scan_record(session, request, user_id)

    if scan.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建扫描记录失败"
        )

    # 2. 异步执行扫描和处理
    background_task.add_task(process_fofa_scan, scan.id, request)

    return FofaScanResponse(
        scan_id=scan.id,
        status=FofaScanStatus.RUNNING,
        query=scan.query,
        country=scan.country,
        total_found=0,
        total_created=0,
        message="FOFA扫描已启动，正在后台处理",
    )


async def process_fofa_scan(scan_id: int, request: FofaScanRequest):
    """
    后台处理FOFA扫描

    Args:
        scan_id: 扫描记录ID
        request: 扫描请求
    """
    async with sessionmanager.session() as session:
        scan = await session.get(FofaScanDB, scan_id)
        if not scan:
            logger.error(f"扫描记录不存在: {scan_id}")
            return

        try:
            # 更新状态为运行中
            scan.status = FofaScanStatus.RUNNING
            await session.commit()

            # 1. 调用FOFA API
            client = FofaClient()
            html_content = await client.search(request.country, request.custom_query)

            # 2. 解析主机列表
            parser = FofaHTMLParser()
            hosts = parser.extract_hosts(html_content)

            scan.total_found = len(hosts)
            await session.commit()

            # 3. 批量创建endpoint
            created_count = 0
            for host in hosts:
                try:
                    endpoint = await create_or_update_endpoint(
                        session, EndpointCreateWithName(url=host, name=host)
                    )
                    created_count += 1

                    # 4. 可选：自动触发检测
                    if request.auto_test and endpoint.id:
                        await create_test_task(
                            session,
                            endpoint.id,
                            scheduled_at=now() + timedelta(seconds=request.test_delay_seconds),
                        )
                        logger.debug(f"已为端点 {endpoint.id} 创建检测任务")
                except Exception as e:
                    logger.error(f"创建端点失败 {host}: {e}")
                    continue

            # 5. 更新扫描结果
            scan.total_created = created_count
            scan.status = FofaScanStatus.COMPLETED
            scan.completed_at = now()
            await session.commit()

            logger.info(
                f"FOFA扫描完成: {scan_id}, 发现 {len(hosts)}, 成功创建 {created_count}"
            )

        except Exception as e:
            logger.error(f"FOFA扫描失败 {scan_id}: {e}")
            scan.status = FofaScanStatus.FAILED
            scan.error_message = str(e)
            scan.completed_at = now()
            await session.commit()


async def get_scan_result(session: DBSessionDep, scan_id: int) -> FofaScanInfo:
    """
    获取扫描结果

    Args:
        session: 数据库会话
        scan_id: 扫描记录ID

    Returns:
        扫描记录信息

    Raises:
        HTTPException: 当扫描记录不存在时
    """
    scan = await session.get(FofaScanDB, scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="扫描记录不存在")

    return FofaScanInfo(
        id=scan.id,
        query=scan.query,
        country=scan.country,
        status=scan.status,
        total_found=scan.total_found,
        total_created=scan.total_created,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
        error_message=scan.error_message,
    )


async def list_scans(session: DBSessionDep, limit: int = 20, offset: int = 0) -> List[FofaScanInfo]:
    """
    获取扫描历史

    Args:
        session: 数据库会话
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        扫描记录列表
    """
    query = select(FofaScanDB).order_by(FofaScanDB.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    scans = result.scalars().all()

    return [
        FofaScanInfo(
            id=scan.id,
            query=scan.query,
            country=scan.country,
            status=scan.status,
            total_found=scan.total_found,
            total_created=scan.total_created,
            created_at=scan.created_at,
            completed_at=scan.completed_at,
            error_message=scan.error_message,
        )
        for scan in scans
    ]

