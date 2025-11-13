import asyncio
import json
from typing import Optional

from aiohttp import ClientResponseError
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import exists
from sqlmodel import select

from src.ai_model.models import AIModelDB, AIModelStatusEnum, EndpointAIModelDB
from src.apikey.models import ApiKeyDB
from src.apikey.service import (
    check_rate_limits,
    get_api_key_from_request,
    log_api_key_usage,
)
from src.database import DBSessionDep
from src.endpoint.models import EndpointDB
from src.logging import get_logger
from src.utils import now

from .client import OllamaClient

logger = get_logger(__name__)

STREAM_BY_DEFAULT_ROUTES = ["api/generate", "api/chat"]


class RequestInfo(BaseModel):
    full_path: str
    method: str
    request: Optional[dict] = None
    headers: dict
    params: dict
    model_name: str
    model_tag: str
    stream: bool

    @classmethod
    async def from_request(cls, full_path: str, request_raw: Request) -> "RequestInfo":
        # Get possible request parameters
        full_path = full_path.strip("/")
        model_name = full_path.split("/")[-1]
        stream = full_path in STREAM_BY_DEFAULT_ROUTES
        request = None
        method = request_raw.method
        try:
            request = await request_raw.json()
            logger.debug(f"Request body: {request}")
            model_name = request.get("model")
            stream = request.get("stream", stream)
        except Exception as e:
            logger.warning(f"Decoding request body failed: {e}")
            pass
        logger.info(f"Request for model: {model_name}, stream: {stream}")

        headers = {
            key: value
            for key, value in request_raw.headers.items()
            if key.lower() not in ["host", "content-length", "authorization"]
        }
        params = dict(request_raw.query_params)

        if not model_name or ":" not in model_name:
            raise HTTPException(status_code=400, detail="Invalid model name")

        name, tag = model_name.split(":")

        return cls(
            full_path=full_path,
            method=method,
            request=request,
            headers=headers,
            params=params,
            model_name=name,
            model_tag=tag,
            stream=stream,
        )


async def get_tags(
    session: DBSessionDep,
):
    query = select(AIModelDB.name, AIModelDB.tag)
    subquery = select(EndpointAIModelDB).where(
        (EndpointAIModelDB.ai_model_id == AIModelDB.id)
        & (EndpointAIModelDB.status == AIModelStatusEnum.AVAILABLE)
    )
    query = query.where(exists(subquery))
    result = await session.execute(query)

    response = {"models": []}
    for row in result.all():
        name = row[0]
        tag = row[1]
        response["models"].append({"model": f"{name}:{tag}", "name": f"{name}:{tag}"})
    return response


async def send_request_to_endpoints(
    request_info: RequestInfo,
    session: DBSessionDep,
    api_key: ApiKeyDB,
    endpoints: list[EndpointDB],
):
    # Create a function to log the API key usage after the request completes
    async def log_usage(session: DBSessionDep, status_code):
        if api_key.id is None:
            return
        await log_api_key_usage(
            session,
            api_key.id,
            request_info.full_path,
            request_info.method,
            request_info.model_name,
            status_code,
        )

    if request_info.stream:

        async def stream_response(session: DBSessionDep):
            error = HTTPException(500, "Fail to connect to endpoint")
            for endpoint in endpoints:
                logger.info(f"Sending request to endpoint: {endpoint.url}")
                try:
                    async with OllamaClient(endpoint.url).connect() as client:
                        generator = await client._request(
                            request_info.method,
                            request_info.full_path,
                            json=request_info.request,
                            headers=request_info.headers,
                            params=request_info.params,
                            stream=True,
                        )
                        async with asyncio.timeout(10):
                            first_response = await generator.__anext__()
                            yield first_response

                        async for response in generator:
                            yield response
                    # Log successful request
                    logger.info(f"Request to endpoint {endpoint.url} completed")
                    await log_usage(session, 200)
                    return
                except Exception as e:
                    logger.error(f"Error sending request to endpoint {endpoint.url}: {type(e).__name__}: {str(e)[:1000]}")
                    error = e

            try:
                raise error
            except ClientResponseError as e:
                error_msg = str(e.message) if hasattr(e, 'message') else str(e)
                logger.error(f"Error from endpoint: {e.status} - {error_msg}")
                await log_usage(session, e.status)
                yield f"data: {json.dumps({'error': {'message': error_msg, 'status': e.status}})}\n\n"
            except Exception as e:
                logger.error(f"Error: {e}")
                await log_usage(session, 500)
                yield "Error: Failed to connect to the endpoint"

        return StreamingResponse(stream_response(session), media_type="text/event-stream")
    else:
        error = HTTPException(500, "Fail to connect to endpoint")
        for endpoint in endpoints:
            logger.info(f"Sending request to endpoint: {endpoint.url}")
            try:
                async with OllamaClient(endpoint.url).connect() as client:
                    response = await client._request(
                        request_info.method,
                        request_info.full_path,
                        json=request_info.request,
                        headers=request_info.headers,
                        params=request_info.params,
                    )
                    logger.info(f"Request to endpoint {endpoint.url} completed")
                    await log_usage(session, 200)
                    return PlainTextResponse(response)
            except Exception as e:
                error = e
        try:
            raise error
        except ClientResponseError as e:
            logger.error(f"Error: {e.status} {e.message}")
            await log_usage(session, e.status)
            raise HTTPException(status_code=e.status, detail=e.message) from e
        except Exception as e:
            logger.error(f"Error: {e}")
            await log_usage(session, 500)
            raise HTTPException(
                status_code=500, detail="Error: Failed to connect to the endpoint"
            ) from e


async def request_forwarding(
    full_path: str, request_raw: Request, session: DBSessionDep
) -> StreamingResponse | PlainTextResponse | JSONResponse:
    match full_path.strip("/"):
        case "":
            return PlainTextResponse("Hello, World!")
        case "api/tags":
            return JSONResponse(await get_tags(session))
        case "v1/models":
            tags = await get_tags(session)
            timestamp = int(now().timestamp())
            result = {
                "object": "list",
                "data": [
                    {
                        "id": model["model"],
                        "object": "model",
                        "owned_by": "user",
                        "created": timestamp,
                    }
                    for model in tags["models"]
                ],
            }
            return JSONResponse(result)

    from src.endpoint.service import (
        get_ai_model_by_name_and_tag,
        get_best_endpoints_for_model,
    )
    from src.setting.service import get_setting
    from src.setting.models import SystemSettingKey
    from src.user.models import UserDB
    from src.plan.models import PlanDB

    # 检查是否禁用 API 鉴权
    disable_auth = False
    try:
        auth_setting = await get_setting(session, SystemSettingKey.DISABLE_OLLAMA_API_AUTH)
        disable_auth = auth_setting.value.lower() == "true"
    except HTTPException:
        # 如果设置不存在，使用默认值（需要鉴权）
        disable_auth = False

    # Get and validate API key（如果未禁用鉴权）
    if disable_auth:
        # 创建一个虚拟的 API key、user 和 plan 对象
        # 使用一个默认的管理员用户和计划
        from src.plan.service import get_user_plan
        
        # 尝试获取第一个管理员用户
        admin_user_query = select(UserDB).where(UserDB.is_admin == True).limit(1)
        admin_user_result = await session.execute(admin_user_query)
        admin_user = admin_user_result.scalar_one_or_none()
        
        if not admin_user:
            raise HTTPException(status_code=500, detail="No admin user found for disabled auth mode")
        
        # 获取该用户的计划
        plan = await get_user_plan(session, admin_user)
        
        # 创建一个虚拟的 API key 对象（不保存到数据库）
        api_key = ApiKeyDB(
            id=None,  # 虚拟 ID，设为 None 以避免数据库操作
            key="disabled_auth",
            user_id=admin_user.id,
            revoked=False,
        )
        user = admin_user
    else:
        # 正常鉴权流程
        api_key, user, plan = await get_api_key_from_request(request_raw, session)

        await session.refresh(api_key)
        await session.refresh(user)
        await session.refresh(plan)

        if api_key.id is None:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if not user.is_admin:
            # Check rate limits
            await check_rate_limits(session, api_key, plan)

    # Get request data
    logger.info(f"Received request for path: {full_path}")

    try:
        request_info = await RequestInfo.from_request(full_path, request_raw)

        # Get model
        model = await get_ai_model_by_name_and_tag(
            session, request_info.model_name, request_info.model_tag
        )

        if not model.id:
            raise HTTPException(status_code=404, detail="Model not found")

        # Get best endpoint
        endpoints = await get_best_endpoints_for_model(session, model.id)

        try:
            return await send_request_to_endpoints(request_info, session, api_key, endpoints)
        except Exception as e:
            logger.error(f"Error: {e}")
            raise e
    except HTTPException as e:
        # 只有在启用鉴权时才记录 API key 使用情况
        if api_key.id is not None:
            await log_api_key_usage(
                session,
                api_key.id,
                full_path,
                request_raw.method,
                request_info.model_name if 'request_info' in locals() else None,
                e.status_code,
            )
        raise e
    except Exception as e:
        # 只有在启用鉴权时才记录 API key 使用情况
        if api_key.id is not None:
            await log_api_key_usage(
                session,
                api_key.id,
                full_path,
                request_raw.method,
                request_info.model_name if 'request_info' in locals() else None,
                500,
            )
        raise HTTPException(
            status_code=500, detail="Error: Failed to connect to the endpoint"
        ) from e
