from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api.routes import router
from app.services.fetcher import URLFetcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=5.0,
            read=10.0,
            write=10.0,
            pool=5.0,
        ),
        follow_redirects=True,
        max_redirects=5,
    )

    app.state.http_client = client
    app.state.fetcher = URLFetcher(client)

    yield

    await client.aclose()


app = FastAPI(
    title="Epsilon URL Data Extraction",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)