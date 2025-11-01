from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .crud import analytics_summary
from .database import get_db
from .db_init import init_db
from .routers import (
    analytics,
    cash_flow,
    investment_log,
    master_data,
    ocr_pending,
    product_tracker,
    simulation_lab,
)

app = FastAPI(title="Personal Finance & Investment System")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

app.include_router(cash_flow.router)
app.include_router(investment_log.router)
app.include_router(product_tracker.router)
app.include_router(master_data.router)
app.include_router(simulation_lab.router)
app.include_router(analytics.router)
app.include_router(ocr_pending.router)


@app.on_event("startup")
async def startup_event():
    init_db()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    summary = analytics_summary(db)
    return templates.TemplateResponse("dashboard.html", {"request": request, "summary": summary})
