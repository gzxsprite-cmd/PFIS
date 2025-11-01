from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def analytics_home(request: Request, db: Session = Depends(get_db)):
    summary = crud.analytics_summary(db)
    monthly = crud.monthly_cashflow(db)
    chart_data = json.dumps({"labels": [row[0] for row in monthly], "values": [row[1] for row in monthly]})
    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "summary": summary,
            "chart_data": chart_data,
        },
    )
