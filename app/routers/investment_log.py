from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..schemas import InvestmentLogCreate

router = APIRouter(prefix="/investment", tags=["Investment Log"])
templates = Jinja2Templates(directory="app/templates")


def _render_table(request: Request, db: Session) -> HTMLResponse:
    investments = crud.list_investments(db)
    return templates.TemplateResponse(
        "investment_log/list.html",
        {"request": request, "investments": investments},
    )


@router.get("", response_class=HTMLResponse)
async def page(request: Request, db: Session = Depends(get_db)):
    master_data = crud.list_master_data(db)
    investments = crud.list_investments(db)
    return templates.TemplateResponse(
        "investment_log/index.html",
        {
            "request": request,
            "investments": investments,
            "master_data": master_data,
        },
    )


@router.get("/form", response_class=HTMLResponse)
async def form(request: Request, db: Session = Depends(get_db)):
    master_data = crud.list_master_data(db)
    products = crud.list_products(db)
    return templates.TemplateResponse(
        "investment_log/form.html",
        {
            "request": request,
            "master_data": master_data,
            "products": products,
        },
    )


@router.post("", response_class=HTMLResponse)
async def create(
    request: Request,
    db: Session = Depends(get_db),
    date_value: str = Form(...),
    product_id: int = Form(...),
    action_id: int = Form(...),
    amount: float = Form(...),
    channel_account_id: Optional[int] = Form(default=None),
    remark: Optional[str] = Form(default=None),
):
    payload = InvestmentLogCreate(
        date=date.fromisoformat(date_value),
        product_id=product_id,
        action_id=action_id,
        amount=amount,
        channel_account_id=channel_account_id,
        remark=remark or None,
    )
    crud.create_investment(db, payload)
    return _render_table(request, db)


@router.delete("/{record_id}", response_class=HTMLResponse)
async def delete_record(request: Request, record_id: int, db: Session = Depends(get_db)):
    crud.soft_delete_investment(db, record_id)
    return _render_table(request, db)
