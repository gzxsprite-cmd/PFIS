from __future__ import annotations

from collections import defaultdict
from datetime import date
import json
from typing import Any, Optional


from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..schemas import CashFlowCreate
from ..services.ai_client import AIClientError, AIClientTimeout, call_ai
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


def _normalize_flow_type(flow_type: str | None) -> str:
    raw = (flow_type or "").strip().lower()
    if raw in {value.lower() for value in crud.INCOME_TYPES}:
        return "income"
    if raw in {value.lower() for value in crud.EXPENSE_TYPES}:
        return "expense"
    return "other"


def _build_filter_label(
    start_month: Optional[str],
    end_month: Optional[str],
    range_months: Optional[int],
) -> str:
    if range_months:
        return f"近{range_months}个月"
    if start_month and end_month:
        return f"{start_month} ~ {end_month}"
    return "全部时间"


def _build_analysis_payload(
    records: list[Any],
    start_month: Optional[str],
    end_month: Optional[str],
    range_months: Optional[int],
) -> dict[str, Any]:
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    category_stats: dict[str, dict[str, dict[str, float]]] = {
        "income": defaultdict(lambda: {"amount": 0.0, "count": 0}),
        "expense": defaultdict(lambda: {"amount": 0.0, "count": 0}),
    }
    remark_pool: dict[str, list[str]] = defaultdict(list)

    for item in records:
        flow_type = _normalize_flow_type(item.flow_type)
        if flow_type not in {"income", "expense"}:
            continue

        month_key = item.date.strftime("%Y-%m")
        amount = abs(float(item.amount or 0))
        monthly[month_key][flow_type] += amount

        category_name = item.category.name if item.category else "未分类"
        category_stats[flow_type][category_name]["amount"] += amount
        category_stats[flow_type][category_name]["count"] += 1

        remark = (item.remark or "").strip()
        if remark and len(remark_pool[f"{flow_type}:{category_name}"]) < 5:
            remark_pool[f"{flow_type}:{category_name}"].append(remark)

    def _top(flow: str) -> list[dict[str, Any]]:
        items = sorted(
            category_stats[flow].items(),
            key=lambda pair: pair[1]["amount"],
            reverse=True,
        )[:5]
        return [
            {
                "category": name,
                "amount": round(stat["amount"], 2),
                "count": int(stat["count"]),
            }
            for name, stat in items
        ]

    monthly_rows = [
        {
            "month": month,
            "income": round(values["income"], 2),
            "expense": round(values["expense"], 2),
            "net": round(values["income"] - values["expense"], 2),
        }
        for month, values in sorted(monthly.items())
    ]

    return {
        "range": {
            "start_month": start_month,
            "end_month": end_month,
            "preset": range_months,
            "label": _build_filter_label(start_month, end_month, range_months),
        },
        "summary": {
            "records": len(records),
            "income_total": round(sum(row["income"] for row in monthly.values()), 2),
            "expense_total": round(sum(row["expense"] for row in monthly.values()), 2),
        },
        "monthly": monthly_rows,
        "expense_top": _top("expense"),
        "income_top": _top("income"),
        "remark_samples": dict(remark_pool),
    }


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
    filter_label = _build_filter_label(start_month, end_month, range_months)
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
                "status": "error",
                "message": "月份格式错误，请使用 YYYY-MM。",
                "analysis": "",
                "start_month": start_month or "",
                "end_month": end_month or "",
                "range_label": filter_label,
            },
        )

    if not records:
        return templates.TemplateResponse(
            "cash_flow/ai_analysis_result.html",
            {
                "request": request,
                "status": "empty",
                "message": "当前筛选范围暂无数据可分析。",
                "analysis": "",
                "start_month": start_month or "",
                "end_month": end_month or "",
                "range_label": filter_label,
            },
        )

    payload = _build_analysis_payload(records, start_month, end_month, range_months)
    prompt = (
        "你是一名中文个人财务分析助手。请基于给定的聚合收支数据输出简明分析。\n"
        "请按以下结构输出：\n"
        "1. 支出TOP项（按金额）\n"
        "2. 收入TOP项（按金额）\n"
        "3. 月度波动结论（指出异常月份）\n"
        "4. 三条可执行优化建议（具体到行为）\n"
        "要求：结论清晰，避免空泛。\n\n"
        f"数据(JSON)：{json.dumps(payload, ensure_ascii=False)}"
    )

    try:
        analysis = call_ai(prompt)
        status = "ok"
        message = ""
        if not analysis:
            status = "error"
            message = "AI 未返回有效内容，请稍后重试。"
    except AIClientTimeout:
        status = "timeout"
        analysis = ""
        message = "AI 分析暂时不可用：请求超时（中国本地网络可能不稳定）。请稍后重试。"
    except AIClientError as exc:
        status = "error"
        analysis = ""
        message = f"AI 分析失败：{exc}"
    except Exception as exc:  # noqa: BLE001
        status = "error"
        analysis = ""
        message = f"AI 分析失败：{exc}"

    return templates.TemplateResponse(
        "cash_flow/ai_analysis_result.html",
        {
            "request": request,
            "status": status,
            "message": message,
            "analysis": analysis,
            "start_month": start_month or "",
            "end_month": end_month or "",
            "range_label": filter_label,
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
