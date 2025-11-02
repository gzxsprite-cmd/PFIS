from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..schemas import CashFlowCreate
from ..utils import encode_header_value

router = APIRouter(prefix="/cash_flow", tags=["Cash Flow"])
templates = Jinja2Templates(directory="app/templates")


def _load_master(db: Session):
    return crud.list_master_data(db)


def _render_table(request: Request, db: Session) -> HTMLResponse:
    cashflows = crud.list_cash_flows(db)
    return templates.TemplateResponse(
        "cash_flow/list.html",
        {
            "request": request,
            "cashflows": cashflows,
        },
    )


def _render_row(request: Request, cashflow) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/_table_row.html",
        {
            "request": request,
            "row_template": "cash_flow/row.html",
            "item": cashflow,
        },
    )


@router.get("", response_class=HTMLResponse)
async def page(request: Request, db: Session = Depends(get_db)):
    cashflows = crud.list_cash_flows(db)
    return templates.TemplateResponse(
        "cash_flow/index.html",
        {
            "request": request,
            "cashflows": cashflows,
        },
    )


@router.get("/add_form", response_class=HTMLResponse)
async def add_form(request: Request, db: Session = Depends(get_db)):
    master_data = _load_master(db)
    return templates.TemplateResponse(
        "partials/_edit_modal.html",
        {
            "request": request,
            "title": "新增收支记录",
            "form_action": "/cash_flow",
            "form_template": "cash_flow/_form_fields.html",
            "hx_target": "#cashflow-table",
            "hx_swap": "innerHTML",
            "master_data": master_data,
            "form_id": "cashflow-new",
            "submit_label": "保存",
        },
    )


@router.post("", response_class=HTMLResponse)
async def create(
    request: Request,
    db: Session = Depends(get_db),
    date_value: str = Form(...),
    account_id: int = Form(...),
    category_id: Optional[int] = Form(default=None),
    flow_type: str = Form(...),
    amount: float = Form(...),
    source_type_id: Optional[int] = Form(default=None),
    remark: Optional[str] = Form(default=None),
):
    payload = CashFlowCreate(
        date=date.fromisoformat(date_value),
        account_id=account_id,
        category_id=category_id,
        flow_type=flow_type,
        amount=amount,
        source_type_id=source_type_id,
        remark=remark or None,
    )
    crud.create_cash_flow(db, payload)
    response = _render_table(request, db)
    response.headers["HX-Toast"] = encode_header_value("收支记录已保存")
    return response


@router.delete("/{record_id}", response_class=HTMLResponse)
async def delete_record(request: Request, record_id: int, db: Session = Depends(get_db)):
    crud.soft_delete_cashflow(db, record_id)
    response = _render_table(request, db)
    response.headers["HX-Toast"] = encode_header_value("收支记录已删除")
    return response


@router.get("/edit/{record_id}", response_class=HTMLResponse)
async def edit_record(request: Request, record_id: int, db: Session = Depends(get_db)):
    cashflow = crud.get_cash_flow(db, record_id)
    if not cashflow:
        raise HTTPException(status_code=404, detail="记录不存在")
    master_data = crud.list_master_data(db)
    return templates.TemplateResponse(
        "partials/_edit_modal.html",
        {
            "request": request,
            "title": "编辑收支记录",
            "form_action": f"/cash_flow/{record_id}",
            "form_template": "cash_flow/_form_fields.html",
            "hx_target": f"#cashflow-row-{record_id}",
            "hx_swap": "outerHTML",
            "master_data": master_data,
            "item": cashflow,
            "form_id": f"cashflow-{record_id}",
        },
    )


@router.post("/{record_id}", response_class=HTMLResponse)
async def update_record(
    request: Request,
    record_id: int,
    db: Session = Depends(get_db),
    date_value: str = Form(...),
    account_id: int = Form(...),
    category_id: Optional[int] = Form(default=None),
    flow_type: str = Form(...),
    amount: float = Form(...),
    source_type_id: Optional[int] = Form(default=None),
    remark: Optional[str] = Form(default=None),
):
    payload = CashFlowCreate(
        date=date.fromisoformat(date_value),
        account_id=account_id,
        category_id=category_id,
        flow_type=flow_type,
        amount=amount,
        source_type_id=source_type_id,
        remark=remark or None,
    )
    cashflow = crud.update_cash_flow(db, record_id, payload)
    if not cashflow:
        raise HTTPException(status_code=404, detail="记录不存在")
    response = _render_row(request, cashflow)
    response.headers["HX-Toast"] = encode_header_value("收支记录已更新")
    return response
