import pytest
import socket

from app.security.url_validator import (
    URLBlockedError,
    URLValidationError,
    URLValidator,
)


@pytest.fixture
def validator():
    return URLValidator()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://example.com",
        "https://example.com/path",
        "https://example.com:8080/path?query=value",
    ],
)
async def test_validate_accepts_valid_http_urls(validator, url):
    validator._resolve_hostname = lambda hostname: [
        "93.184.216.34"
    ]

    await validator.validate(url)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "",
        "example.com",
        "ftp://example.com",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "http://",
        "https://",
    ],
)
async def test_validate_rejects_invalid_urls(validator, url):
    with pytest.raises(URLValidationError):
        await validator.validate(url)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://127.0.0.2:8080",
        "http://10.0.0.1",
        "http://172.16.0.1",
        "http://192.168.1.1",
        "http://169.254.169.254",
        "http://[::1]",
    ],
)
async def test_validate_blocks_private_or_special_ip_addresses(
    validator,
    url,
):
    with pytest.raises(URLBlockedError):
        await validator.validate(url)


@pytest.mark.asyncio
async def test_validate_accepts_hostname_resolving_to_public_ip(validator):
    validator._resolve_hostname = lambda hostname: [
        "93.184.216.34"
    ]

    await validator.validate("https://example.com")


@pytest.mark.asyncio
async def test_validate_blocks_hostname_resolving_to_private_ip(validator):
    validator._resolve_hostname = lambda hostname: [
        "10.0.0.5"
    ]

    with pytest.raises(URLBlockedError):
        await validator.validate("https://example.com")


@pytest.mark.asyncio
async def test_validate_blocks_hostname_if_any_resolved_ip_is_blocked(
    validator,
):
    validator._resolve_hostname = lambda hostname: [
        "93.184.216.34",
        "192.168.1.10",
    ]

    with pytest.raises(URLBlockedError):
        await validator.validate("https://example.com")

@pytest.mark.asyncio
async def test_validate_rejects_hostname_when_dns_resolution_fails(
    validator,
    monkeypatch,
):
    def getaddrinfo(*args, **kwargs):
        raise socket.gaierror

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)

    with pytest.raises(URLValidationError):
        await validator.validate("https://example.com")