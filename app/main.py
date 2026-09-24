from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api.errors import (
    handle_fetch_error,
    handle_fetch_timeout,
    handle_invalid_url,
    handle_response_too_large,
    handle_too_many_redirects,
    handle_url_blocked,
    handle_unsupported_content_type,
)
from app.api.routes import router
from app.security.url_validator import URLBlockedError, URLValidationError, URLValidator
from app.services.extraction import ExtractionService, UnsupportedContentTypeError
from app.services.fetcher import (
    FetchError,
    FetchTimeoutError,
    ResponseTooLargeError,
    TooManyRedirectsError,
    URLFetcher,
)
from app.services.parser import HTMLParser


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=5.0,
            read=10.0,
            write=10.0,
            pool=5.0,
        ),
    )

    url_validator = URLValidator()
    fetcher = URLFetcher(
        client=client,
        url_validator=url_validator,
    )
    parser = HTMLParser()
    extraction_service = ExtractionService(
        fetcher=fetcher,
        parser=parser,
    )

    app.state.http_client = client
    app.state.url_validator = url_validator
    app.state.fetcher = fetcher
    app.state.parser = parser
    app.state.extraction_service = extraction_service

    yield

    await client.aclose()


app = FastAPI(
    title="Epsilon URL Data Extraction",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_exception_handler(URLValidationError, handle_invalid_url)
app.add_exception_handler(URLBlockedError, handle_url_blocked)
app.add_exception_handler(ResponseTooLargeError, handle_response_too_large)
app.add_exception_handler(UnsupportedContentTypeError, handle_unsupported_content_type)
app.add_exception_handler(FetchTimeoutError, handle_fetch_timeout)
app.add_exception_handler(FetchError, handle_fetch_error)
app.add_exception_handler(TooManyRedirectsError, handle_too_many_redirects)

app.include_router(router)