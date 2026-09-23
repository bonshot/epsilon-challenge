from app.services.parser import HTMLParser


def test_parse_extracts_title_description_and_text():
    html = b"""
    <html>
        <head>
            <title>Example Page</title>
            <meta name="description" content="A test page">
        </head>
        <body>
            <h1>Hello world</h1>
            <p>This is an example page.</p>
        </body>
    </html>
    """

    parser = HTMLParser()

    result = parser.parse(
        html,
        "https://example.com",
    )

    assert result.title == "Example Page"
    assert result.description == "A test page"
    assert result.text == "Hello world\n\nThis is an example page."


def test_parse_removes_non_content_elements():
    html = b"""
    <html>
        <head>
            <style>
                body { color: red; }
            </style>
        </head>
        <body>
            <h1>Hello</h1>

            <script>
                console.log("should not appear");
            </script>

            <p>World</p>

            <noscript>
                JavaScript is required
            </noscript>
        </body>
    </html>
    """

    parser = HTMLParser()

    result = parser.parse(
        html,
        "https://example.com",
    )

    assert result.text == "Hello\n\nWorld"


def test_parse_resolves_relative_links():
    html = b"""
    <html>
        <body>
            <a href="/about">About us</a>
            <a href="products">Products</a>
            <a href="https://other.com">Other site</a>
        </body>
    </html>
    """

    parser = HTMLParser()

    result = parser.parse(
        html,
        "https://example.com/shop/page",
    )

    assert result.links[0].text == "About us"
    assert result.links[0].url == "https://example.com/about"

    assert result.links[1].text == "Products"
    assert result.links[1].url == "https://example.com/shop/products"

    assert result.links[2].text == "Other site"
    assert result.links[2].url == "https://other.com"


def test_parse_ignores_non_http_links():
    html = b"""
    <html>
        <body>
            <a href="#section">Section</a>
            <a href="mailto:test@example.com">Email</a>
            <a href="tel:+123456789">Phone</a>
            <a href="javascript:void(0)">Click</a>
            <a href="/valid">Valid link</a>
        </body>
    </html>
    """

    parser = HTMLParser()

    result = parser.parse(
        html,
        "https://example.com",
    )

    assert len(result.links) == 1
    assert result.links[0].text == "Valid link"
    assert result.links[0].url == "https://example.com/valid"


def test_parse_returns_none_when_title_and_description_are_missing():
    html = b"""
    <html>
        <body>
            <p>Hello world</p>
        </body>
    </html>
    """

    parser = HTMLParser()

    result = parser.parse(
        html,
        "https://example.com",
    )

    assert result.title is None
    assert result.description is None
    assert result.text == "Hello world"