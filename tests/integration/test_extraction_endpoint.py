import pytest
from fastapi.testclient import TestClient

from unittest.mock import AsyncMock
from app.main import app
from app.security.url_validator import (
    URLBlockedError,
    URLValidationError,
)
from app.services.fetcher import (
    FetchError,
    FetchResult,
    FetchTimeoutError,
    ResponseTooLargeError,
    TooManyRedirectsError,
)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_fetch():
    original_fetch = app.state.fetcher.fetch

    mock = AsyncMock()
    app.state.fetcher.fetch = mock

    yield mock

    app.state.fetcher.fetch = original_fetch


def test_extract_url_returns_extracted_page(client, mock_fetch):
    mock_fetch.return_value = FetchResult(
        requested_url="https://example.com",
        final_url="https://example.com/",
        status_code=200,
        content_type="text/html",
        content=b"""
            <html>
                <head>
                    <title>Example Page</title>
                    <meta
                        name="description"
                        content="Example description"
                    >
                </head>
                <body>
                    <h1>Hello World</h1>
                    <p>This is a test page.</p>
                    <a href="/about">About</a>
                </body>
            </html>
        """,
    )

    response = client.post(
        "/extract",
        json={"url": "https://example.com"},
    )

    assert response.status_code == 200

    assert response.json() == {
        "requested_url": "https://example.com",
        "final_url": "https://example.com/",
        "status_code": 200,
        "title": "Example Page",
        "description": "Example description",
        "text": "Hello World\n\nThis is a test page.\n\nAbout",
        "links": [
            {
                "text": "About",
                "url": "https://example.com/about",
            }
        ],
    }


def test_extract_url_returns_400_for_invalid_url(client, mock_fetch):
    mock_fetch.side_effect = URLValidationError

    response = client.post(
        "/extract",
        json={"url": "ftp://example.com"},
    )

    assert response.status_code == 400

    assert response.json() == {
        "error": {
            "code": "INVALID_URL",
            "message": "The provided URL is invalid.",
        }
    }


def test_extract_url_returns_403_for_blocked_url(client, mock_fetch):
    mock_fetch.side_effect = URLBlockedError

    response = client.post(
        "/extract",
        json={"url": "http://127.0.0.1:8000"},
    )

    assert response.status_code == 403

    assert response.json() == {
        "error": {
            "code": "URL_BLOCKED",
            "message": "The provided URL is not allowed.",
        }
    }


def test_extract_url_returns_504_for_fetch_timeout(client, mock_fetch):
    mock_fetch.side_effect = FetchTimeoutError

    response = client.post(
        "/extract",
        json={"url": "https://example.com"},
    )

    assert response.status_code == 504

    assert response.json() == {
        "error": {
            "code": "FETCH_TIMEOUT",
            "message": "The target server did not respond within the allowed time.",
        }
    }


def test_extract_url_returns_413_for_large_response(client, mock_fetch):
    mock_fetch.side_effect = ResponseTooLargeError

    response = client.post(
        "/extract",
        json={"url": "https://example.com"},
    )

    assert response.status_code == 413

    assert response.json() == {
        "error": {
            "code": "RESPONSE_TOO_LARGE",
            "message": "The target response exceeds the maximum allowed size.",
        }
    }


def test_extract_url_returns_415_for_unsupported_content_type(
    client,
    mock_fetch,
):
    mock_fetch.return_value = FetchResult(
        requested_url="https://example.com/data.json",
        final_url="https://example.com/data.json",
        status_code=200,
        content_type="application/json",
        content=b'{"message": "hello"}',
    )

    response = client.post(
        "/extract",
        json={"url": "https://example.com/data.json"},
    )

    assert response.status_code == 415

    assert response.json() == {
        "error": {
            "code": "UNSUPPORTED_CONTENT_TYPE",
            "message": "The target resource is not a supported HTML document.",
        }
    }


def test_extract_url_returns_502_for_fetch_error(client, mock_fetch):
    mock_fetch.side_effect = FetchError

    response = client.post(
        "/extract",
        json={"url": "https://example.com"},
    )

    assert response.status_code == 502

    assert response.json() == {
        "error": {
            "code": "FETCH_ERROR",
            "message": "The target resource could not be fetched.",
        }
    }


def test_extract_url_returns_502_for_too_many_redirects(
    client,
    mock_fetch,
):
    mock_fetch.side_effect = TooManyRedirectsError

    response = client.post(
        "/extract",
        json={"url": "https://example.com"},
    )

    assert response.status_code == 502

    assert response.json() == {
        "error": {
            "code": "TOO_MANY_REDIRECTS",
            "message": "The target URL exceeded the maximum allowed redirects.",
        }
    }


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}