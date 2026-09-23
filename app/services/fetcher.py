from dataclasses import dataclass

import httpx


class FetchError(Exception):
    """Raised when a target URL cannot be fetched successfully."""


class FetchTimeoutError(FetchError):
    """Raised when fetching a target URL exceeds the configured timeout."""


class ResponseTooLargeError(FetchError):
    """Raised when a target response exceeds the configured size limit."""


@dataclass
class FetchResult:
    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    content: bytes


class URLFetcher:
    def __init__(
        self,
        client: httpx.AsyncClient,
        max_response_size: int = 5 * 1024 * 1024,
    ):
        self.client = client
        self.max_response_size = max_response_size

    async def fetch(self, url: str) -> FetchResult:
        try:
            async with self.client.stream("GET", url) as response:
                content_length = response.headers.get("content-length")

                if content_length is not None:
                    if int(content_length) > self.max_response_size:
                        raise ResponseTooLargeError

                content = bytearray()

                async for chunk in response.aiter_bytes():
                    content.extend(chunk)

                    if len(content) > self.max_response_size:
                        raise ResponseTooLargeError

        except httpx.TimeoutException as exc:
            raise FetchTimeoutError from exc
        except httpx.RequestError as exc:
            raise FetchError from exc

        return FetchResult(
            requested_url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=response.headers.get("content-type", ""),
            content=bytes(content),
        )