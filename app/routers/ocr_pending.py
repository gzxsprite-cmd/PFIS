from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db

router = APIRouter(prefix="/ocr", tags=["OCR Pending"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def ocr_list(request: Request, db: Session = Depends(get_db)):
    items = crud.list_ocr_pending(db)
    return templates.TemplateResponse(
        "ocr_pending.html",
        {
            "request": request,
            "items": items,
        },
    )
