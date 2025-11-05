from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Env, get_config
from .database import create_db_and_tables, ensure_database_exists, sessionmanager
from .endpoint.scheduler import get_scheduler
from .logging import get_logger
from .routes import router
from .setting.service import init_settings


config = get_config()
logger = get_logger(__name__)

logger.debug(f"Config: {config}")

# no doc other than dev env
docs_url = "/docs" if config.app.env == Env.DEV else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")

    # Ensure database exists
    await ensure_database_exists()

    # Initialize database
    await create_db_and_tables()

    # Initialize settings
    async with sessionmanager.session() as session:
        await init_settings(session)

    # Initialize and start scheduler
    scheduler = get_scheduler()
    await scheduler.start()
    logger.info("Application startup complete")

    yield

    # Shutdown scheduler
    scheduler = get_scheduler()
    await scheduler.shutdown()

    # Close database connections
    if sessionmanager._engine is not None:
        await sessionmanager.close()

    logger.info("Application shutdown complete")


app = FastAPI(
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=None,
    title="Ollama Hack Backend",
    description="Ollama Hack Backend",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
