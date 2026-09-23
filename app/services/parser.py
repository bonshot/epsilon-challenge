from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


@dataclass
class ParsedLink:
    text: str
    url: str


@dataclass
class ParsedPage:
    title: str | None
    description: str | None
    text: str
    links: list[ParsedLink]


class HTMLParser:
    """Parse an HTML document into structured page data."""

    def parse(self, html: bytes, base_url: str) -> ParsedPage:
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_title(soup)
        description = self._extract_description(soup)

        self._remove_non_content_elements(soup)

        text = self._extract_text(soup)
        links = self._extract_links(soup, base_url)

        return ParsedPage(
            title=title,
            description=description,
            text=text,
            links=links,
        )

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        if soup.title is None:
            return None

        title = soup.title.get_text(" ", strip=True)

        return title or None

    def _extract_description(self, soup: BeautifulSoup) -> str | None:
        meta = soup.find(
            "meta",
            attrs={"name": lambda value: value and value.lower() == "description"},
        )

        if meta is None:
            return None

        description = meta.get("content", "").strip()

        return description or None

    def _remove_non_content_elements(self, soup: BeautifulSoup) -> None:
        for element in soup(
            ["title", "script", "style", "noscript", "template", "svg"]
        ):
            element.decompose()

    def _extract_text(self, soup: BeautifulSoup) -> str:
        text = soup.get_text(separator="\n", strip=True)

        lines = [line.strip() for line in text.splitlines() if line.strip()]

        return "\n\n".join(lines)

    def _extract_links(
        self,
        soup: BeautifulSoup,
        base_url: str,
    ) -> list[ParsedLink]:
        links = []

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            text = anchor.get_text(" ", strip=True)

            if not href or not text:
                continue

            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            absolute_url = urljoin(base_url, href)
            parsed_url = urlparse(absolute_url)

            if parsed_url.scheme not in {"http", "https"}:
                continue

            links.append(
                ParsedLink(
                    text=text,
                    url=absolute_url,
                )
            )

        return links