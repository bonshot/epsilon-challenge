# Epsilon URL Data Extraction Challenge

## Objective

Build an HTTP API that receives a URL, downloads the corresponding web page, extracts structured information, and returns it as JSON

The service focuses on HTML/XHTML pages and provides:

* Page metadata
* Human-readable text
* Extracted links
* Final URL after redirects
* HTTP status code

The implementation also includes request limits and SSRF protections because the service performs server-side HTTP requests against user-provided URLs

## Architecture

The application follows a layered architecture:

```text
Client
  │
  ▼
FastAPI Router
  │
  ▼
ExtractionService
  │
  ├── URL validation / SSRF protection
  │
  ├── HTTP Fetcher
  │
  └── HTML Parser
```

### Main components

* **API layer**: exposes the HTTP endpoints and maps application errors to HTTP responses
* **Extraction service**: orchestrates fetching, content validation, parsing, and response construction
* **URL validator**: validates URL schemes, resolves hostnames, and blocks unsafe network destinations
* **HTTP fetcher**: performs asynchronous HTTP requests, handles redirects, timeouts, and response-size limits
* **HTML parser**: extracts metadata, visible text, and links from the returned HTML document

The HTTP client is created during application startup and reused throughout the application lifecycle to allow connection reuse. It is closed during application shutdown

## API

### `POST /extract`

Extract information from a web page

#### Request

```json
{
  "url": "https://example.com"
}
```

#### Successful response

```json
{
  "requested_url": "https://example.com",
  "final_url": "https://example.com/",
  "status_code": 200,
  "title": "Example Domain",
  "description": "Example Domain",
  "text": "This domain is for use in illustrative examples...",
  "links": [
    {
      "text": "More information...",
      "url": "https://www.iana.org/domains/example"
    }
  ]
}
```

`requested_url` and `final_url` are kept separately to make redirects explicit and preserve the original client input

### Errors

Errors follow a common structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

The API currently exposes the following application errors:

| HTTP status | Code                       | Description                                           |
| ----------- | -------------------------- | ----------------------------------------------------- |
| 400         | `INVALID_URL`              | The URL is invalid or cannot be resolved              |
| 403         | `URL_BLOCKED`              | The URL resolves to a blocked network destination     |
| 413         | `RESPONSE_TOO_LARGE`       | The target response exceeds the configured size limit |
| 415         | `UNSUPPORTED_CONTENT_TYPE` | The target resource is not HTML/XHTML                 |
| 502         | `FETCH_ERROR`              | The target resource could not be fetched              |
| 502         | `TOO_MANY_REDIRECTS`       | The redirect limit was exceeded                       |
| 504         | `FETCH_TIMEOUT`            | The target server exceeded the configured timeout     |

## Health Check

### `GET /health`

Returns:

```json
{
  "status": "ok"
}
```

## Getting Started

### Requirements

* Python 3.10+
* pip

### Installation

Clone the repository and create a virtual environment:

```bash
git clone <repository-url>
cd epsilon-challenge

python3 -m venv .venv
source .venv/bin/activate
```

Install the project dependencies:

```bash
pip install -e .
```

For development and testing dependencies:

```bash
pip install -e ".[dev]"
```

### Running the API

Start the application with:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI's interactive documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Testing

Run the complete test suite with:

```bash
pytest -q
```

The test suite contains both unit and integration tests

### Unit tests

Unit tests cover individual application components, including:

* URL validation
* SSRF protection
* HTTP fetching
* Redirect handling
* Response size limits
* Timeout and network errors
* HTML parsing
* Extraction service behavior

### Integration tests

Integration tests exercise the HTTP API and verify:

* Successful extraction
* Error-to-HTTP status mapping
* Unsupported content types
* Fetch failures
* Timeout handling
* Response size errors
* Redirect errors
* Health checks

External HTTP requests are mocked in integration tests so the test suite does not depend on external services

## Design Decisions

### Asynchronous HTTP requests

The API uses `httpx.AsyncClient` because fetching external resources is an I/O-bound operation

Using an asynchronous client allows the application to handle other requests while waiting for external servers to respond

DNS resolution through `socket.getaddrinfo` is blocking, so hostname resolution is executed using `asyncio.to_thread` to avoid blocking the FastAPI event loop

### Manual redirect handling

Automatic redirect following is intentionally disabled

Each redirect target is validated before the next request is performed. This is important because an initially safe public URL could redirect to a private or otherwise restricted network address

For example:

```text
https://example.com
       │
       ▼
https://another-site.com
       │
       ▼
http://127.0.0.1/admin
```

The final target is validated independently and is rejected before the request is sent

Redirects are limited to a configurable maximum of 5 redirects

### SSRF protection

The API accepts user-provided URLs and therefore performs potentially attacker-controlled server-side requests

The URL validator:

1. Allows only HTTP and HTTPS schemes
2. Validates that a hostname exists
3. Detects literal IP addresses
4. Resolves hostnames before making the request
5. Rejects private, loopback, link-local, reserved, and unspecified addresses
6. Repeats validation for every redirect target

Examples of blocked destinations include:

* `127.0.0.1`
* `10.0.0.0/8`
* `172.16.0.0/12`
* `192.168.0.0/16`
* `169.254.0.0/16`
* `::1`
* `::`
* IPv6 private/link-local ranges

The implementation mitigates common SSRF cases but does not claim to completely eliminate every possible DNS-based race condition. In particular, DNS validation and the subsequent HTTP connection may involve separate hostname resolutions. Fully eliminating this class of race would require tighter control over how the validated address is bound to the actual connection

### Response size limits

Responses are streamed instead of loading the complete response into memory immediately

The fetcher checks `Content-Length` when available and also enforces the limit while reading the response body

The default maximum response size is:

```text
5 MiB
```

The streaming check is necessary because `Content-Length` may be missing or inaccurate

### Timeouts

External requests use explicit timeouts:

| Timeout         |    Default |
| --------------- | ---------: |
| Connect         |  5 seconds |
| Read            | 10 seconds |
| Write           | 10 seconds |
| Connection pool |  5 seconds |

These values are configurable defaults chosen for this challenge

### Content-Type validation

The HTTP fetcher is intentionally generic and does not decide what type of resource the extraction service should process

The extraction service validates the returned `Content-Type` and currently accepts:

* `text/html`
* `application/xhtml+xml`

This keeps HTTP fetching separate from extraction-specific requirements

### Static HTML parsing

HTML is parsed with BeautifulSoup

The parser extracts:

* `<title>`
* `<meta name="description">`
* Human-readable text
* HTTP/HTTPS links

Non-content elements such as scripts, styles, templates, SVGs, and noscript elements are removed before text extraction

Relative links are resolved against the final URL after redirects

## Initial Assumptions

### Supported content

* The service accepts HTTP and HTTPS URLs
* Only HTML/XHTML resources are processed
* Client-side JavaScript is not executed
* "Relevant information" is interpreted as metadata, human-readable text, and links rather than semantic article extraction
* Fetched pages are not persisted

### Statelessness

The API does not maintain request-specific persistent state

Multiple instances can therefore process requests independently, which allows horizontal scaling at the application level

## Limitations

### JavaScript-rendered content

The parser processes the HTML returned by the server and does not execute JavaScript

Pages that render their main content entirely through client-side JavaScript may therefore return incomplete content

Supporting these pages would require a browser automation solution such as a headless Chromium-based browser, which would introduce additional CPU, memory, latency, and operational complexity

### Semantic content extraction

The current parser does not attempt to determine which parts of a page are the "main article" or most relevant content

For example, navigation menus, headers, and footers may be included in the extracted text

A future implementation could introduce semantic extraction using DOM heuristics or an LLM-based extraction layer

### DNS rebinding

The current SSRF protection validates DNS resolution before making the request, but the actual HTTP connection can perform another DNS resolution. This leaves a theoretical DNS rebinding race  

A stronger implementation could resolve the hostname once and explicitly bind the HTTP connection to the validated address while preserving the correct HTTP Host header and TLS SNI

## Future Improvements

Possible extensions include:

* Configuration through environment variables
* Structured logging and request tracing
* Metrics for latency, failures, redirects, and response sizes
* More comprehensive SSRF protection
* Browser-based rendering for JavaScript-heavy pages
* Semantic content extraction
* Caching of repeated requests
* Rate limiting
* Authentication and authorization if exposed publicly
* Background processing for expensive extraction tasks

These features are intentionally outside the current MVP in order to keep the core extraction pipeline small, understandable, and testable
