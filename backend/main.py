from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import connect_db, close_db
from app.api.routes import auth
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="ATLARS API",
    description="Adaptive Temporal Life Analysis & Reflection System",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "version": "0.1.0"}
