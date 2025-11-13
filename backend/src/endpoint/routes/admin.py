from typing import Optional, cast

from fastapi import APIRouter, Depends, HTTPException, status

from src.endpoint.models import EndpointDB, EndpointTestTask
from src.endpoint.schemas import (
    BatchOperationResult,
    EndpointInfo,
    TaskInfo,
)
from src.endpoint.service import (
    batch_create_or_update_endpoints,
    batch_delete_endpoints,
    batch_test_endpoints,
    create_or_update_endpoint,
    delete_endpoint,
    get_latest_task_for_endpoint,
    get_task_by_id,
    manual_trigger_endpoint_test,
    test_all_endpoints,
    update_endpoint,
)
from src.user.service import get_current_admin_user

endpoint_admin_router = APIRouter(tags=["endpoint"], dependencies=[Depends(get_current_admin_user)])


@endpoint_admin_router.post(
    "/",
    response_model=EndpointInfo,
    status_code=status.HTTP_201_CREATED,
    description="Create a new endpoint",
    response_description="The created endpoint",
)
async def _create_endpoint(
    endpoint: EndpointDB = Depends(create_or_update_endpoint),
) -> EndpointInfo:
    return EndpointInfo(**endpoint.model_dump())


@endpoint_admin_router.patch(
    "/{endpoint_id:int}",
    response_model=EndpointInfo,
    description="Update an endpoint",
    response_description="The updated endpoint",
    dependencies=[Depends(get_current_admin_user)],
)
async def _update_endpoint(
    endpoint: EndpointDB = Depends(update_endpoint),
) -> EndpointInfo:
    return EndpointInfo(**endpoint.model_dump())


@endpoint_admin_router.delete(
    "/{endpoint_id:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete an endpoint",
    dependencies=[Depends(get_current_admin_user)],
)
async def _delete_endpoint(
    endpoint_id: int,
    deleted: None = Depends(delete_endpoint),
) -> None:
    return None


@endpoint_admin_router.post(
    "/batch",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    description="Batch create or update endpoints",
    response_description="The created or updated endpoints",
    dependencies=[Depends(get_current_admin_user)],
)
async def _batch_create_endpoints(
    endpoints: None = Depends(batch_create_or_update_endpoints),
) -> None:
    return None


@endpoint_admin_router.post(
    "/{endpoint_id:int}/test",
    response_model=TaskInfo,
    status_code=status.HTTP_202_ACCEPTED,
    description="Manually trigger a test for an endpoint",
    response_description="The created test task",
)
async def _trigger_endpoint_test(
    task: Optional[EndpointTestTask] = Depends(manual_trigger_endpoint_test),
) -> TaskInfo:
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not created")
    return TaskInfo(**task.model_dump())


@endpoint_admin_router.get(
    "/{endpoint_id:int}/task",
    response_model=TaskInfo,
    description="Get the latest task for an endpoint",
    response_description="The latest task for an endpoint",
)
async def _get_latest_task(
    task: EndpointTestTask = Depends(get_latest_task_for_endpoint),
) -> TaskInfo:
    return TaskInfo(
        id=cast(int, task.id),
        endpoint_id=task.endpoint_id,
        status=task.status,
        scheduled_at=task.scheduled_at,
        last_tried=task.last_tried,
        created_at=task.created_at,
    )


@endpoint_admin_router.get(
    "/tasks/{task_id:int}",
    response_model=TaskInfo,
    description="Get a task by ID with its endpoint",
    response_description="The task with its endpoint",
)
async def _get_task_by_id(
    task: EndpointTestTask = Depends(get_task_by_id),
) -> TaskInfo:
    return TaskInfo(
        id=cast(int, task.id),
        endpoint_id=task.endpoint_id,
        status=task.status,
        scheduled_at=task.scheduled_at,
        last_tried=task.last_tried,
        created_at=task.created_at,
    )


@endpoint_admin_router.post(
    "/batch-test",
    response_model=BatchOperationResult,
    status_code=status.HTTP_202_ACCEPTED,
    description="Batch test multiple endpoints",
    response_description="Result of batch test operation",
    dependencies=[Depends(get_current_admin_user)],
)
async def _batch_test_endpoints(
    batch_operation_result: BatchOperationResult = Depends(batch_test_endpoints),
) -> BatchOperationResult:
    return batch_operation_result


@endpoint_admin_router.post(
    "/batch-test/all",
    response_model=BatchOperationResult,
    status_code=status.HTTP_202_ACCEPTED,
    description="Test all endpoints",
    response_description="Result of testing all endpoints",
    dependencies=[Depends(get_current_admin_user)],
)
async def _test_all_endpoints(
    batch_operation_result: BatchOperationResult = Depends(test_all_endpoints),
) -> BatchOperationResult:
    return batch_operation_result


@endpoint_admin_router.delete(
    "/batch",
    response_model=BatchOperationResult,
    status_code=status.HTTP_200_OK,
    description="Batch delete multiple endpoints",
    response_description="Result of batch delete operation",
    dependencies=[Depends(get_current_admin_user)],
)
async def _batch_delete_endpoints(
    batch_operation_result: BatchOperationResult = Depends(batch_delete_endpoints),
) -> BatchOperationResult:
    return batch_operation_result
