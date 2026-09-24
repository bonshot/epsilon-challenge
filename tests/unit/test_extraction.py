from unittest.mock import AsyncMock, Mock

import pytest

from app.services.extraction import (
    ExtractionService,
    UnsupportedContentTypeError,
)
from app.services.fetcher import FetchResult
from app.services.parser import ParsedLink, ParsedPage


@pytest.fixture
def fetcher():
    return Mock()


@pytest.fixture
def parser():
    return Mock()


@pytest.fixture
def service(fetcher, parser):
    return ExtractionService(
        fetcher=fetcher,
        parser=parser,
    )


@pytest.mark.asyncio
async def test_extract_fetches_and_parses_page(
    service,
    fetcher,
    parser,
):
    fetcher.fetch = AsyncMock(
        return_value=FetchResult(
            requested_url="https://example.com",
            final_url="https://example.com/page",
            status_code=200,
            content_type="text/html; charset=utf-8",
            content=b"<html>...</html>",
        )
    )

    parser.parse.return_value = ParsedPage(
        title="Example",
        description="Example page",
        text="Hello world",
        links=[
            ParsedLink(
                text="More information",
                url="https://example.org",
            )
        ],
    )

    result = await service.extract("https://example.com")

    fetcher.fetch.assert_awaited_once_with(
        "https://example.com",
    )

    parser.parse.assert_called_once_with(
        html=b"<html>...</html>",
        base_url="https://example.com/page",
    )

    assert result.requested_url == "https://example.com"
    assert result.final_url == "https://example.com/page"
    assert result.status_code == 200
    assert result.title == "Example"
    assert result.description == "Example page"
    assert result.text == "Hello world"

    assert len(result.links) == 1
    assert result.links[0].text == "More information"
    assert result.links[0].url == "https://example.org"


@pytest.mark.asyncio
async def test_extract_rejects_unsupported_content_type(
    service,
    fetcher,
    parser,
):
    fetcher.fetch = AsyncMock(
        return_value=FetchResult(
            requested_url="https://example.com/file.pdf",
            final_url="https://example.com/file.pdf",
            status_code=200,
            content_type="application/pdf",
            content=b"%PDF...",
        )
    )

    with pytest.raises(UnsupportedContentTypeError):
        await service.extract("https://example.com/file.pdf")

    parser.parse.assert_not_called()


@pytest.mark.asyncio
async def test_extract_accepts_xhtml(
    service,
    fetcher,
    parser,
):
    fetcher.fetch = AsyncMock(
        return_value=FetchResult(
            requested_url="https://example.com",
            final_url="https://example.com",
            status_code=200,
            content_type="application/xhtml+xml",
            content=b"<html></html>",
        )
    )

    parser.parse.return_value = ParsedPage(
        title=None,
        description=None,
        text="",
        links=[],
    )

    result = await service.extract("https://example.com")

    assert result.status_code == 200
    parser.parse.assert_called_once()


@pytest.mark.asyncio
async def test_extract_propagates_fetch_error(
    service,
    fetcher,
):
    fetcher.fetch = AsyncMock(
        side_effect=RuntimeError("fetch failed"),
    )

    with pytest.raises(RuntimeError, match="fetch failed"):
        await service.extract("https://example.com")