import asyncio
import socket
from ipaddress import ip_address
from urllib.parse import ParseResult, urlparse


class URLValidationError(Exception):
    """Raised when a URL does not satisfy the API security requirements."""


class URLBlockedError(URLValidationError):
    """Raised when a URL resolves to a blocked network address."""


class URLValidator:
    """Validate URLs before allowing server-side HTTP requests."""

    ALLOWED_SCHEMES = {"http", "https"}

    async def validate(self, url: str) -> None:
        parsed_url = urlparse(url)

        self._validate_scheme(parsed_url)
        self._validate_hostname(parsed_url)

        hostname = parsed_url.hostname

        if self._is_ip_address(hostname):
            self._validate_ip(hostname)
            return

        addresses = await asyncio.to_thread(
            self._resolve_hostname,
            hostname,
        )

        self._validate_resolved_addresses(addresses)

    def _validate_scheme(self, parsed_url: ParseResult) -> None:
        if parsed_url.scheme not in self.ALLOWED_SCHEMES:
            raise URLValidationError

    def _validate_hostname(self, parsed_url: ParseResult) -> None:
        if not parsed_url.hostname:
            raise URLValidationError

    def _is_ip_address(self, hostname: str) -> bool:
        try:
            ip_address(hostname)
            return True
        except ValueError:
            return False

    def _validate_ip(self, hostname: str) -> None:
        address = ip_address(hostname)

        if self._is_blocked_address(address):
            raise URLBlockedError

    def _resolve_hostname(self, hostname: str) -> list[str]:
        try:
            results = socket.getaddrinfo(
                hostname,
                None,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise URLValidationError from exc

        return list({result[4][0] for result in results})

    def _validate_resolved_addresses(
        self,
        addresses: list[str],
    ) -> None:
        if not addresses:
            raise URLValidationError

        for address in addresses:
            parsed_address = ip_address(address)

            if self._is_blocked_address(parsed_address):
                raise URLBlockedError

    def _is_blocked_address(self, address) -> bool:
        return (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_unspecified
        )