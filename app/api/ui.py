"""Browser entry point for the Meridian Compass employee interface."""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.config import REPOSITORY_ROOT


router = APIRouter(include_in_schema=False)
INDEX_PATH = REPOSITORY_ROOT / "app" / "templates" / "index.html"


@router.get("/", response_class=FileResponse)
async def meridian_compass_ui() -> FileResponse:
    return FileResponse(INDEX_PATH, media_type="text/html")
