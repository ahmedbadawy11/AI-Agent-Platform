import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

from routes import api

from helpers.config import get_settings
from stores.LLM import OpenAIProvider

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


def _setup_logging():
    """Configure logging so app and library loggers (e.g. OpenAI errors) show in the terminal."""
    try:
        level_name = get_settings().LOG_LEVEL.upper()
        level = getattr(logging, level_name, logging.INFO)
    except Exception:
        level = logging.INFO
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        root.addHandler(handler)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # optional: reduce access log noise


_setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    postgres_conn = (
        f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    )
    app.db_engine = create_async_engine(postgres_conn)
    app.db_client = sessionmaker(
        app.db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    app.openai_provider = OpenAIProvider(
        api_key=settings.OPENAI_API_KEY,
        default_generation_max_output_tokens=settings.GENERATION_DAFAULT_MAX_TOKENS,
        default_generation_temperature=settings.GENERATION_DAFAULT_TEMPERATURE,
        elevenlabs_api_key=settings.ELEVENLABS_API_KEY,
        elevenlabs_voice_id=settings.ELEVENLABS_VOICE_ID,
    )
    app.openai_provider.set_generation_model(model_id=settings.GENERATION_MODEL_ID)
 
    app.openai_provider.set_stt_model(getattr(settings, "STT_MODEL_ID", "whisper-1") or "whisper-1")
    app.openai_provider.stt_language = getattr(settings, "STT_LANGUAGE", None) or None
    app.openai_provider.set_tts_model(getattr(settings, "TTS_MODEL_ID", "tts-1") or "tts-1")
    app.openai_provider.tts_voice = getattr(settings, "TTS_VOICE", "alloy") or "alloy"
    logger.info("Application startup complete (DB and OpenAI provider ready).")
    yield
    await app.db_engine.dispose()
    logger.info("Application shutdown complete.")


app = FastAPI(title="AI Agent Platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def serve_ui():
        return FileResponse(static_dir / "index.html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Avoid 404 when the browser requests a favicon."""
    return Response(status_code=204)


app.include_router(api.api_router, prefix="/api/v1")













