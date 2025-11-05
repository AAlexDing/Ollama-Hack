from fastapi import APIRouter

from .ai_model import ai_model_router
from .apikey import apikey_router
from .endpoint import endpoint_router
from .fofa import fofa_router
from .ollama import ollama_router
from .plan import plan_router
from .setting import setting_router
from .subscription import subscription_router
from .user import user_router

api_router = APIRouter(prefix="/api/v2")

api_router.include_router(user_router)
api_router.include_router(endpoint_router)
api_router.include_router(ai_model_router)
api_router.include_router(apikey_router)
api_router.include_router(plan_router)
api_router.include_router(setting_router)
api_router.include_router(fofa_router)
api_router.include_router(subscription_router)

router = APIRouter()

router.include_router(api_router)
router.include_router(ollama_router)
