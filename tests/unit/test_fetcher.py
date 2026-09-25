import httpx
import pytest

from app.security.url_validator import URLBlockedError, URLValidator
from app.services.fetcher import (
    FetchError,
    FetchTimeoutError,
    ResponseTooLargeError,
    TooManyRedirectsError,
    URLFetcher,
)


@pytest.fixture
def validator(monkeypatch):
    validator = URLValidator()

    monkeypatch.setattr(
        validator,
        "_resolve_hostname",
        lambda hostname: ["93.184.216.34"],
    )

    return validator

@pytest.fixture
def fetcher(validator):
    def handler(request):
        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/html"},
            content=b"<html><body>Hello</body></html>",
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    )

    return URLFetcher(
        client=client,
        url_validator=validator,
    )


@pytest.mark.asyncio
async def test_fetch_returns_response(fetcher):
    result = await fetcher.fetch("https://example.com")

    assert result.requested_url == "https://example.com"
    assert result.final_url == "https://example.com"
    assert result.status_code == 200
    assert result.content_type == "text/html"
    assert result.content == b"<html><body>Hello</body></html>"


@pytest.mark.asyncio
async def test_fetch_rejects_response_too_large(fetcher):
    fetcher.max_response_size = 10

    with pytest.raises(ResponseTooLargeError):
        await fetcher.fetch("https://example.com")


@pytest.mark.asyncio
async def test_fetch_rejects_response_with_large_content_length(validator):
    def handler(request):
        return httpx.Response(
            status_code=200,
            headers={
                "content-type": "text/html",
                "content-length": "100",
            },
            content=b"small",
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    )

    fetcher = URLFetcher(
        client=client,
        url_validator=validator,
        max_response_size=10,
    )

    with pytest.raises(ResponseTooLargeError):
        await fetcher.fetch("https://example.com")


@pytest.mark.asyncio
async def test_fetch_raises_timeout(validator):
    def handler(request):
        raise httpx.ReadTimeout("Request timed out")

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    )

    fetcher = URLFetcher(
        client=client,
        url_validator=validator,
    )

    with pytest.raises(FetchTimeoutError):
        await fetcher.fetch("https://example.com")


@pytest.mark.asyncio
async def test_fetch_raises_fetch_error(validator):
    def handler(request):
        raise httpx.ConnectError("Connection failed")

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    )

    fetcher = URLFetcher(
        client=client,
        url_validator=validator,
    )

    with pytest.raises(FetchError):
        await fetcher.fetch("https://example.com")


@pytest.mark.asyncio
async def test_fetch_follows_redirect(validator):
    requested_urls = []

    def handler(request):
        requested_urls.append(str(request.url))

        if request.url.path == "/":
            return httpx.Response(
                status_code=301,
                headers={"location": "/new-page"},
            )

        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/html"},
            content=b"<html><body>Final page</body></html>",
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    )

    fetcher = URLFetcher(
        client=client,
        url_validator=validator,
    )

    result = await fetcher.fetch("https://example.com")

    assert requested_urls == [
        "https://example.com",
        "https://example.com/new-page",
    ]
    assert result.final_url == "https://example.com/new-page"
    assert result.status_code == 200
    assert result.content == b"<html><body>Final page</body></html>"


@pytest.mark.asyncio
async def test_fetch_follows_absolute_redirect(validator):
    requested_urls = []

    def handler(request):
        requested_urls.append(str(request.url))

        if request.url.host == "example.com":
            return httpx.Response(
                status_code=302,
                headers={"location": "https://example.org/page"},
            )

        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/html"},
            content=b"final content",
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    )

    fetcher = URLFetcher(
        client=client,
        url_validator=validator,
    )

    result = await fetcher.fetch("https://example.com")

    assert requested_urls == [
        "https://example.com",
        "https://example.org/page",
    ]
    assert result.final_url == "https://example.org/page"


@pytest.mark.asyncio
async def test_fetch_blocks_redirect_to_private_ip(validator):
    requested_urls = []

    def handler(request):
        requested_urls.append(str(request.url))

        return httpx.Response(
            status_code=302,
            headers={"location": "http://127.0.0.1/admin"},
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    )

    fetcher = URLFetcher(
        client=client,
        url_validator=validator,
    )

    with pytest.raises(URLBlockedError):
        await fetcher.fetch("https://example.com")

    assert requested_urls == [
        "https://example.com",
    ]


@pytest.mark.asyncio
async def test_fetch_rejects_too_many_redirects(validator):
    requested_urls = []

    def handler(request):
        requested_urls.append(str(request.url))

        return httpx.Response(
            status_code=302,
            headers={"location": str(request.url)},
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    )

    fetcher = URLFetcher(
        client=client,
        url_validator=validator,
        max_redirects=2,
    )

    with pytest.raises(TooManyRedirectsError):
        await fetcher.fetch("https://example.com")

    assert len(requested_urls) == 3

@pytest.mark.asyncio
async def test_fetch_returns_redirect_response_without_location(validator):
    def handler(request):
        return httpx.Response(
            status_code=302,
            headers={"content-type": "text/html"},
            content=b"redirect response",
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    )

    fetcher = URLFetcher(
        client=client,
        url_validator=validator,
    )

    result = await fetcher.fetch("https://example.com")

    assert result.status_code == 302
    assert result.final_url == "https://example.com"
    assert result.content == b"redirect response"