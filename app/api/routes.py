from fastapi import APIRouter, Request

from app.schemas.extraction import ExtractRequest, PageResponse

router = APIRouter()


@router.post("/extract", response_model=PageResponse)
async def extract_url(
    request: ExtractRequest,
    http_request: Request,
) -> PageResponse:
    service = http_request.app.state.extraction_service

    return await service.extract(request.url)


@router.get("/health")
async def health_check()  -> dict[str, str]:
    return {"status": "ok"}