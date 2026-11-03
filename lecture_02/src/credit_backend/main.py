from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from credit_backend.decisions.dependencies import build_service
from credit_backend.decisions.router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.service = build_service()
    yield


app = FastAPI(title="Credit Decision Backend", lifespan=lifespan)
app.include_router(router)
