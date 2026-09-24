from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from app.security.url_validator import URLValidator


class FetchError(Exception):
    """Raised when a target URL cannot be fetched successfully."""


class FetchTimeoutError(FetchError):
    """Raised when fetching a target URL exceeds the configured timeout."""


class ResponseTooLargeError(FetchError):
    """Raised when a target response exceeds the configured size limit."""


class TooManyRedirectsError(FetchError):
    """Raised when a target URL exceeds the configured redirect limit."""


@dataclass
class FetchResult:
    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    content: bytes


class URLFetcher:
    REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}

    def __init__(
        self,
        client: httpx.AsyncClient,
        url_validator: URLValidator,
        max_response_size: int = 5 * 1024 * 1024,
        max_redirects: int = 5,
    ):
        self.client = client
        self.url_validator = url_validator
        self.max_response_size = max_response_size
        self.max_redirects = max_redirects

    async def fetch(self, url: str) -> FetchResult:
        current_url = url

        for redirect_count in range(self.max_redirects + 1):
            await self.url_validator.validate(current_url)

            response = await self._fetch_response(current_url)

            if response.status_code not in self.REDIRECT_STATUS_CODES:
                return FetchResult(
                    requested_url=url,
                    final_url=current_url,
                    status_code=response.status_code,
                    content_type=response.content_type,
                    content=response.content,
                )

            location = response.location

            if location is None:
                return FetchResult(
                    requested_url=url,
                    final_url=current_url,
                    status_code=response.status_code,
                    content_type=response.content_type,
                    content=response.content,
                )

            if redirect_count >= self.max_redirects:
                raise TooManyRedirectsError

            current_url = urljoin(current_url, location)

        raise TooManyRedirectsError

    async def _fetch_response(self, url: str) -> "_ResponseData":
        try:
            async with self.client.stream("GET", url) as response:
                content_length = response.headers.get("content-length")

                if content_length is not None:
                    try:
                        content_length_value = int(content_length)
                    except ValueError:
                        content_length_value = None

                    if (
                        content_length_value is not None
                        and content_length_value > self.max_response_size
                    ):
                        raise ResponseTooLargeError

                content = bytearray()

                async for chunk in response.aiter_bytes():
                    content.extend(chunk)

                    if len(content) > self.max_response_size:
                        raise ResponseTooLargeError

                return _ResponseData(
                    status_code=response.status_code,
                    content_type=response.headers.get("content-type", ""),
                    content=bytes(content),
                    location=response.headers.get("location"),
                )

        except httpx.TimeoutException as exc:
            raise FetchTimeoutError from exc
        except httpx.RequestError as exc:
            raise FetchError from exc


@dataclass
class _ResponseData:
    status_code: int
    content_type: str
    content: bytes
    location: str | None