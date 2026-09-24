from fastapi import Request
from fastapi.responses import JSONResponse

from app.security.url_validator import (
    URLBlockedError,
    URLValidationError,
)
from app.services.extraction import UnsupportedContentTypeError
from app.services.fetcher import (
    FetchError,
    FetchTimeoutError,
    ResponseTooLargeError,
    TooManyRedirectsError,
)


async def handle_invalid_url(
    request: Request,
    exc: URLValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "INVALID_URL",
                "message": "The provided URL is invalid.",
            }
        },
    )


async def handle_url_blocked(
    request: Request,
    exc: URLBlockedError,
) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "code": "URL_BLOCKED",
                "message": "The provided URL is not allowed.",
            }
        },
    )


async def handle_response_too_large(
    request: Request,
    exc: ResponseTooLargeError,
) -> JSONResponse:
    return JSONResponse(
        status_code=413,
        content={
            "error": {
                "code": "RESPONSE_TOO_LARGE",
                "message": "The target response exceeds the maximum allowed size.",
            }
        },
    )


async def handle_unsupported_content_type(
    request: Request,
    exc: UnsupportedContentTypeError,
) -> JSONResponse:
    return JSONResponse(
        status_code=415,
        content={
            "error": {
                "code": "UNSUPPORTED_CONTENT_TYPE",
                "message": "The target resource is not a supported HTML document.",
            }
        },
    )


async def handle_fetch_timeout(
    request: Request,
    exc: FetchTimeoutError,
) -> JSONResponse:
    return JSONResponse(
        status_code=504,
        content={
            "error": {
                "code": "FETCH_TIMEOUT",
                "message": "The target server did not respond within the allowed time.",
            }
        },
    )


async def handle_fetch_error(
    request: Request,
    exc: FetchError,
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "error": {
                "code": "FETCH_ERROR",
                "message": "The target resource could not be fetched.",
            }
        },
    )


async def handle_too_many_redirects(
    request: Request,
    exc: TooManyRedirectsError,
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "error": {
                "code": "TOO_MANY_REDIRECTS",
                "message": "The target URL exceeded the maximum allowed redirects.",
            }
        },
    )