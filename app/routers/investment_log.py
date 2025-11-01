from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..schemas import CashFlowCreate, InvestmentLogCreate

router = APIRouter(prefix="/investment", tags=["Investment"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def investment_list(request: Request, db: Session = Depends(get_db)):
    investments = crud.list_investments(db)
    master_data = crud.list_master_data(db)
    products = crud.list_products(db)
    return templates.TemplateResponse(
        "investment_log/list.html",
        {
            "request": request,
            "investments": investments,
            "master_data": master_data,
            "products": products,
        },
    )


@router.get("/form", response_class=HTMLResponse)
async def investment_form(
    request: Request, db: Session = Depends(get_db), target: Optional[str] = None
):
    master_data = crud.list_master_data(db)
    products = crud.list_products(db)
    target_selector = f"#{target}" if target else "#investment-table"
    return templates.TemplateResponse(
        "investment_log/form.html",
        {
            "request": request,
            "master_data": master_data,
            "products": products,
            "target_selector": target_selector,
        },
    )


@router.post("/add", response_class=HTMLResponse)
async def investment_add(
    request: Request,
    db: Session = Depends(get_db),
    date_value: str = Form(...),
    product_id: str = Form(...),
    action_id: str = Form(...),
    amount: str = Form(...),
    channel_id: Optional[str] = Form(default=None),
    remark: Optional[str] = Form(default=None),
    create_cashflow: Optional[str] = Form(default=None),
):
    payload = InvestmentLogCreate(
        date=date.fromisoformat(date_value),
        product_id=int(product_id),
        action_id=int(action_id),
        amount=float(amount),
        channel_id=int(channel_id) if channel_id else None,
        remark=remark or None,
    )
    investment = crud.create_investment(db, payload)

    if create_cashflow:
        flow_type = "支出"
        action = investment.action.name if investment.action else ""
        if action == "赎回":
            flow_type = "收入"
        cash_payload = CashFlowCreate(
            date=payload.date,
            account_id=payload.channel_id or 1,
            category_id=None,
            flow_type=flow_type,
            amount=payload.amount,
            source_type_id=None,
            remark=f"来自理财操作#{investment.id}",
            link_investment_id=investment.id,
        )
        crud.create_cash_flow(db, cash_payload)

    investments = crud.list_investments(db)
    return templates.TemplateResponse(
        "investment_log/table.html",
        {
            "request": request,
            "investments": investments,
        },
    )
