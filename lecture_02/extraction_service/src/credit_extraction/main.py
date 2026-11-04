from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from credit_extraction.config import load_settings
from credit_extraction.documents.reader import DocumentReader
from credit_extraction.documents.router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Model B is loaded once, because loading it takes seconds."""
    settings = load_settings()
    app.state.reader = DocumentReader(settings.checkpoint, settings.revision)
    yield


app = FastAPI(title="Information Extraction Service", lifespan=lifespan)
app.include_router(router)