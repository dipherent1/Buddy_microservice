from fastapi import FastAPI
from app.api.routers import agent_router, ai_router
from app.core.logger import setup_logging, get_logger
from app.mcp.client import close_mcp_client, initialize_mcp_client
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
import asyncio
from sqlalchemy import text
from app.infrastructure.db import engine

setup_logging()
logger = get_logger(__name__)

def init_db():
    """Verify DB connectivity and log basic status.

    - Executes a trivial SELECT 1.
    - Optionally attempts to reflect 'users' and 'tokens' tables.
    This avoids heavy reflection of all tables on startup.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connectivity OK.")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return
    

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 FastAPI app started successfully.")
    # --- Startup ----
    try:
        logger.info("Initializing MCP client...")
        init_db()
        await initialize_mcp_client()
        yield
    finally:
        logger.info("🛑 FastAPI app shutting down.")
        # --- Shutdown ----
        try:
            logger.info("Closing MCP client...")
            # Best-effort shutdown with timeout; avoid propagating cancellation during reload/Ctrl+C
            await close_mcp_client(timeout=5.0)
        except asyncio.CancelledError:
            logger.warning("⚠️ Lifespan shutdown cancelled during MCP client close; continuing app shutdown.")
        
app = FastAPI(title="AI Agent Microservice", version='1.0', lifespan=lifespan)

origins = [
    "http://127.0.0.1:8000",
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # or ["*"] temporarily for testing
    allow_credentials=True,
    allow_methods=["*"],            # allow all HTTP methods
    allow_headers=["*"],            # allow all headers (e.g. Content-Type)
)
app.include_router(agent_router.router, prefix="/agent", tags=["Agent"])
app.include_router(ai_router.router, prefix="/ai", tags=["AI"])


@app.get("/")
async def root():
    return {"message": "Welcome to the AI Agent Microservice!"}