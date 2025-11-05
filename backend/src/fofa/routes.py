"""FOFA扫描API路由"""
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends

from src.database import DBSessionDep
from src.user.models import UserDB
from src.user.service import get_current_admin_user

from .schemas import FofaScanInfo, FofaScanRequest, FofaScanResponse
from .service import execute_fofa_scan, get_scan_result, list_scans

router = APIRouter(prefix="/fofa", tags=["FOFA扫描"])


@router.post("/scan", response_model=FofaScanResponse, summary="启动FOFA扫描")
async def scan_fofa(
    request: FofaScanRequest,
    background_task: BackgroundTasks,
    session: DBSessionDep,
    current_user: UserDB = Depends(get_current_admin_user),
):
    """
    启动FOFA扫描（仅管理员）

    - **country**: 目标国家代码（如 US, CN, RU, JP, DE）
    - **custom_query**: 自定义查询语句（可选，会覆盖默认的国家查询）
    - **auto_test**: 是否自动触发检测（默认true）
    - **test_delay_seconds**: 检测延迟秒数（默认5秒）

    示例：
    ```json
    {
      "country": "US",
      "auto_test": true,
      "test_delay_seconds": 10
    }
    ```
    """
    return await execute_fofa_scan(session, background_task, request, current_user.id)


@router.get("/scan/{scan_id}", response_model=FofaScanInfo, summary="获取扫描结果")
async def get_scan(
    scan_id: int,
    session: DBSessionDep,
    current_user: UserDB = Depends(get_current_admin_user),
):
    """
    获取指定扫描的结果

    返回扫描的详细信息，包括：
    - 扫描状态（pending/running/completed/failed）
    - 发现的主机数量
    - 成功创建的端点数量
    - 错误信息（如果有）
    """
    return await get_scan_result(session, scan_id)


@router.get("/scans", response_model=List[FofaScanInfo], summary="获取扫描历史")
async def list_scan_history(
    session: DBSessionDep,
    current_user: UserDB = Depends(get_current_admin_user),
    limit: int = 20,
    offset: int = 0,
):
    """
    获取扫描历史列表

    - **limit**: 返回数量限制（默认20）
    - **offset**: 偏移量（默认0）

    按创建时间倒序返回扫描记录
    """
    return await list_scans(session, limit, offset)

