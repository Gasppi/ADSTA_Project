from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from credit_backend.clients.extraction import ExtractionUnavailableError
from credit_backend.config import Settings
from credit_backend.decisions.dependencies import build_service
from credit_backend.decisions.router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    service = build_service(Settings())
    app.state.service = service
    try:
        yield
    finally:
        service.close()


app = FastAPI(title="Credit Decision Backend", lifespan=lifespan)
app.include_router(router)


@app.exception_handler(ExtractionUnavailableError)
async def extraction_unavailable(
    request: Request, error: ExtractionUnavailableError
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "The Information Extraction Service is not available. Try again."},
    )
