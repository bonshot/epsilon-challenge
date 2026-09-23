import httpx
import pytest

from app.services.fetcher import (
    FetchError,
    FetchTimeoutError,
    ResponseTooLargeError,
    URLFetcher,
)


@pytest.mark.asyncio
async def test_fetch_returns_response_data():
    def handler(request):
        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/html"},
            content=b"<html><body>Hello</body></html>",
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    fetcher = URLFetcher(client)

    result = await fetcher.fetch("https://example.com")

    assert result.requested_url == "https://example.com"
    assert result.final_url == "https://example.com"
    assert result.status_code == 200
    assert result.content_type == "text/html"
    assert result.content == b"<html><body>Hello</body></html>"

    await client.aclose()


@pytest.mark.asyncio
async def test_fetch_rejects_response_that_is_too_large():
    def handler(request):
        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/html"},
            content=b"x" * 100,
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    fetcher = URLFetcher(
        client,
        max_response_size=50,
    )

    with pytest.raises(ResponseTooLargeError):
        await fetcher.fetch("https://example.com")

    await client.aclose()


@pytest.mark.asyncio
async def test_fetch_rejects_response_using_content_length():
    def handler(request):
        return httpx.Response(
            status_code=200,
            headers={
                "content-type": "text/html",
                "content-length": "100",
            },
            content=b"x" * 100,
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    fetcher = URLFetcher(
        client,
        max_response_size=50,
    )

    with pytest.raises(ResponseTooLargeError):
        await fetcher.fetch("https://example.com")

    await client.aclose()


@pytest.mark.asyncio
async def test_fetch_raises_timeout_error():
    def handler(request):
        raise httpx.ReadTimeout("Request timed out")

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    fetcher = URLFetcher(client)

    with pytest.raises(FetchTimeoutError):
        await fetcher.fetch("https://example.com")

    await client.aclose()


@pytest.mark.asyncio
async def test_fetch_raises_fetch_error():
    def handler(request):
        raise httpx.ConnectError("Connection failed")

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    )

    fetcher = URLFetcher(client)

    with pytest.raises(FetchError):
        await fetcher.fetch("https://example.com")

    await client.aclose()