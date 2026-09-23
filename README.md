# Epsilon URL Data Extraction Challenge

## Objective

Build an HTTP API that receives a URL, downloads the corresponding web page, extracts its relevant information, and returns it in a structured JSON format

The service focuses on HTML/XHTML pages and aims to provide human-readable content together with basic page metadata and links

## API Contract

The API exposes a single endpoint for URL extraction

```http
POST /extract
```

Request body:

```json
{
  "url": "https://example.com"
}
```

A successful response contains the original requested URL, the final URL after redirects, the HTTP status code, basic metadata, human-readable text, and extracted links

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

The `requested_url` and `final_url` are kept separately to make redirects explicit and preserve the original client input

## Initial Assumptions

### Supported content

- The service accepts HTTP and HTTPS URLs and processes HTML/XHTML pages

- Client-side JavaScript is not executed, so the extracted content represents the HTML document returned by the server

- The term "relevant content" is interpreted as human-readable text, basic page metadata, and links rather than semantic article extraction

- Fetched pages are not persisted by the service

### Redirects and request limits

- Redirects are supported up to a configurable maximum

- Each redirect target is independently validated before being followed

- External requests use configurable connection and read timeouts

- Responses are subject to a configurable maximum size to prevent unnecessarily large resources from being processed

### Security

- The service rejects requests targeting private, loopback, and link-local network ranges to mitigate Server-Side Request Forgery risks

- URL validation is applied both to the initial URL and to subsequent redirect targets

### Statelessness

- The API does not maintain state between requests, allowing multiple instances of the service to process requests independently or as so called, horizontal scaling
