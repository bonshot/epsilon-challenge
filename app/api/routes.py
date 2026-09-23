from fastapi import APIRouter

from app.schemas.extraction import ExtractRequest, PageResponse

router = APIRouter()


@router.post("/extract", response_model=PageResponse)
async def extract_url(request: ExtractRequest):
    return {
        "requested_url": request.url,
        "final_url": request.url,
        "status_code": 200,
        "title": None,
        "description": None,
        "text": "",
        "links": [],
    }


@router.get("/health")
async def health_check():
    return {"status": "ok"}