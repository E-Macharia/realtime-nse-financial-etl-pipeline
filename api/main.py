import logging
from contextlib import asynccontextmanager
import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from load.db import init_db
from api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("api_main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup database initializations and Redis connection pooling.
    """
    logger.info("Starting up FastAPI application...")
    
    # 1. Initialize database connection
    try:
        init_db()
    except Exception as e:
        logger.critical(f"Failed to initialize database during startup: {e}")
        # We don't crash the server, but log it so dev knows.

    # 2. Initialize Redis connection pool
    app.state.redis = None
    try:
        pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            socket_timeout=2.0
        )
        app.state.redis = redis.Redis(connection_pool=pool)
        app.state.redis.ping()
        logger.info("Connected to Redis successfully for serving caches.")
    except Exception as e:
        logger.warning(
            f"Failed to initialize Redis pool: {e}. FastAPI will fall back to PostgreSQL queries."
        )
        app.state.redis = None

    yield
    
    logger.info("Shutting down FastAPI application...")
    if app.state.redis:
        app.state.redis.close()


app = FastAPI(
    title="NSE Financial Realtime ETL Pipeline API",
    description="Production-grade API serving stock tickers, rolling indicators, alerts and anomalies.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local Streamlit dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(router)
