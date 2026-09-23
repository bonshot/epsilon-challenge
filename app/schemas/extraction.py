from pydantic import BaseModel


class ExtractRequest(BaseModel):
    url: str


class Link(BaseModel):
    text: str
    url: str


class PageResponse(BaseModel):
    requested_url: str
    final_url: str
    status_code: int
    title: str | None
    description: str | None
    text: str
    links: list[Link]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail