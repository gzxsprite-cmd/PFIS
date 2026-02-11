from __future__ import annotations

from datetime import date
from typing import Optional
import os

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


def _query_cashflows(
    db: Session,
    *,
    start_month: Optional[str] = None,
    end_month: Optional[str] = None,
    range_months: Optional[int] = None,
):
    return crud.list_cash_flows_by_period(
        db,
        start_month=start_month,
        end_month=end_month,
        range_months=range_months,
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
            "start_month": "",
            "end_month": "",
        },
    )


@router.get("/table", response_class=HTMLResponse)
async def table(
    request: Request,
    db: Session = Depends(get_db),
    start_month: Optional[str] = None,
    end_month: Optional[str] = None,
    range_months: Optional[int] = None,
):
    try:
        cashflows = _query_cashflows(
            db,
            start_month=start_month,
            end_month=end_month,
            range_months=range_months,
        )
    except ValueError:
        cashflows = []
    return templates.TemplateResponse(
        "cash_flow/list.html",
        {
            "request": request,
            "cashflows": cashflows,
        },
    )


@router.get("/ai_analysis", response_class=HTMLResponse)
async def ai_analysis(
    request: Request,
    db: Session = Depends(get_db),
    start_month: Optional[str] = None,
    end_month: Optional[str] = None,
    range_months: Optional[int] = None,
):
    try:
        records = _query_cashflows(
            db,
            start_month=start_month,
            end_month=end_month,
            range_months=range_months,
        )
    except ValueError:
        return templates.TemplateResponse(
            "cash_flow/ai_analysis_result.html",
            {
                "request": request,
                "analysis": "月份格式错误，请使用 YYYY-MM。",
            },
        )

    if not records:
        return templates.TemplateResponse(
            "cash_flow/ai_analysis_result.html",
            {
                "request": request,
                "analysis": "暂无可分析数据。",
            },
        )

    data = [
        {
            "date": item.date.isoformat(),
            "type": item.flow_type,
            "amount": float(item.amount),
            "category": item.category.name if item.category else "",
            "remark": item.remark or "",
        }
        for item in records
    ]

    prompt = (
        "请分析以下收支数据，输出：\n"
        "1. 支出TOP项\n"
        "2. 收入TOP项\n"
        "3. 支出项月度波动\n"
        "4. 收入项月度波动\n"
        "5. 可执行优化建议\n\n"
        f"数据：{data}"
    )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return templates.TemplateResponse(
            "cash_flow/ai_analysis_result.html",
            {
                "request": request,
                "analysis": "未配置 OPENAI_API_KEY，暂时无法生成 AI 分析。",
            },
        )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model="gpt-5.2",
            input=prompt,
        )
        result = response.output_text or "AI 未返回有效内容，请稍后重试。"
    except Exception as exc:  # noqa: BLE001
        result = f"AI 分析暂时不可用：{exc}"

    return templates.TemplateResponse(
        "cash_flow/ai_analysis_result.html",
        {
            "request": request,
            "analysis": result,
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
