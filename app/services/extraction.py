from app.schemas.extraction import Link, PageResponse
from app.services.fetcher import FetchResult, URLFetcher
from app.services.parser import HTMLParser


class UnsupportedContentTypeError(Exception):
    """Raised when a fetched resource is not a supported HTML document."""


class ExtractionService:
    """Coordinate URL fetching and HTML parsing."""

    SUPPORTED_CONTENT_TYPES = {
        "text/html",
        "application/xhtml+xml",
    }

    def __init__(
        self,
        fetcher: URLFetcher,
        parser: HTMLParser,
    ):
        self.fetcher = fetcher
        self.parser = parser

    async def extract(self, url: str) -> PageResponse:
        result = await self.fetcher.fetch(url)

        self._validate_content_type(result.content_type)

        parsed_page = self.parser.parse(
            html=result.content,
            base_url=result.final_url,
        )

        return PageResponse(
            requested_url=result.requested_url,
            final_url=result.final_url,
            status_code=result.status_code,
            title=parsed_page.title,
            description=parsed_page.description,
            text=parsed_page.text,
            links=[
                Link(
                    text=link.text,
                    url=link.url,
                )
                for link in parsed_page.links
            ],
        )

    def _validate_content_type(self, content_type: str) -> None:
        media_type = content_type.split(";", 1)[0].strip().lower()

        if media_type not in self.SUPPORTED_CONTENT_TYPES:
            raise UnsupportedContentTypeError