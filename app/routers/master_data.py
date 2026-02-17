from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Path, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..schemas import MasterDataCreate
from ..utils import encode_header_value

SELECT_BASE_CLASS = (
    "w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm "
    "focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
)

router = APIRouter(prefix="/master_data", tags=["Master Data"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    master_data = crud.list_master_data(db, include_inactive=True)
    return templates.TemplateResponse(
        "master_data/index.html",
        {
            "request": request,
            "master_data": master_data,
        },
    )


@router.post("", response_class=HTMLResponse)
async def create(
    request: Request,
    db: Session = Depends(get_db),
    table: str = Form(...),
    name: str = Form(...),
):
    payload = MasterDataCreate(table=table, name=name)
    try:
        crud.create_master_data(db, payload)
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    master_data = crud.list_master_data(db, include_inactive=True)
    response = templates.TemplateResponse(
        "master_data/table.html",
        {
            "request": request,
            "table": table,
            "items": master_data.get(_table_key(table), []),
        },
    )
    response.headers["HX-Toast"] = encode_header_value("主数据已新增")
    return response


@router.get("/{table}/{item_id}/edit", response_class=HTMLResponse)
async def edit_item(
    request: Request,
    table: str,
    item_id: int,
    db: Session = Depends(get_db),
):
    item = crud.get_master_item(db, table, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="记录不存在")
    return templates.TemplateResponse(
        "partials/_edit_modal.html",
        {
            "request": request,
            "title": "编辑主数据",
            "form_action": f"/master_data/{table}/{item_id}",
            "form_template": "master_data/_form_fields.html",
            "hx_target": f"#table-{table}",
            "hx_swap": "innerHTML",
            "item": item,
        },
    )


@router.post("/{table}/{item_id}", response_class=HTMLResponse)
async def update_item(
    request: Request,
    table: str,
    item_id: int,
    name: str = Form(...),
    status: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
):
    if not crud.update_master_data(db, table, item_id, name=name, status=status):
        raise HTTPException(status_code=404, detail="记录不存在")
    master_data = crud.list_master_data(db, include_inactive=True)
    response = templates.TemplateResponse(
        "master_data/table.html",
        {
            "request": request,
            "table": table,
            "items": master_data.get(_table_key(table), []),
        },
    )
    response.headers["HX-Toast"] = encode_header_value("主数据已更新")
    return response


@router.post("/{table}/{item_id}/status", response_class=HTMLResponse)
async def update_status(
    request: Request,
    table: str = Path(...),
    item_id: int = Path(...),
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    crud.toggle_master_status(db, table, item_id, status)
    master_data = crud.list_master_data(db, include_inactive=True)
    return templates.TemplateResponse(
        "master_data/table.html",
        {
            "request": request,
            "table": table,
            "items": master_data.get(_table_key(table), []),
        },
    )


@router.post("/{table}/{item_id}/delete", response_class=HTMLResponse)
async def delete_item(
    request: Request,
    table: str,
    item_id: int,
    db: Session = Depends(get_db),
):
    if not crud.soft_delete_master(db, table, item_id):
        raise HTTPException(status_code=404, detail="记录不存在")
    master_data = crud.list_master_data(db, include_inactive=True)
    response = templates.TemplateResponse(
        "master_data/table.html",
        {
            "request": request,
            "table": table,
            "items": master_data.get(_table_key(table), []),
        },
    )
    response.headers["HX-Toast"] = encode_header_value("主数据已删除")
    return response


@router.get("/impact/{table}/{item_id}")
async def impact(table: str, item_id: int, db: Session = Depends(get_db)):
    data = crud.master_impact(db, table, item_id)
    return JSONResponse({"impact": data})


@router.get("/quick_form/{table}", response_class=HTMLResponse)
async def quick_form(
    request: Request,
    table: str,
    field_id: str = Query(..., alias="field_id"),
    field_name: str = Query(..., alias="field_name"),
    include_blank: bool = Query(False, alias="include_blank"),
    blank_label: str = Query("---", alias="blank_label"),
    db: Session = Depends(get_db),
):
    label = _table_label(table)
    if not crud.MASTER_TABLES.get(table):
        raise HTTPException(status_code=400, detail="不支持的主数据类型")
    return templates.TemplateResponse(
        "partials/master_quick_add.html",
        {
            "request": request,
            "table": table,
            "label": label,
            "field_id": field_id,
            "field_name": field_name,
            "include_blank": include_blank,
            "blank_label": blank_label,
        },
    )


@router.post("/quick_add/{table}", response_class=HTMLResponse)
async def quick_add(
    request: Request,
    table: str,
    field_id: str = Form(...),
    field_name: str = Form(...),
    name: str = Form(...),
    include_blank: str = Form("false"),
    blank_label: str = Form("---"),
    db: Session = Depends(get_db),
):
    payload = MasterDataCreate(table=table, name=name)
    try:
        instance = crud.create_master_data(db, payload)
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    items = crud.list_active_master_options(db, table)
    response = templates.TemplateResponse(
        "partials/master_select.html",
        {
            "request": request,
            "table": table,
            "items": items,
            "field_id": field_id,
            "field_name": field_name,
            "selected_id": getattr(instance, "id", None),
            "include_blank": include_blank.lower() == "true",
            "blank_label": blank_label or "---",
            "select_classes": SELECT_BASE_CLASS,
        },
    )
    response.headers["HX-Toast"] = encode_header_value(f"已新增{_table_label(table)}")
    return response


def _table_key(table: str) -> str:
    mapping = {
        "dim_account": "accounts",
        "dim_category": "categories",
        "dim_source_type": "source_types",
        "dim_action_type": "action_types",
        "dim_product_type": "product_types",
        "dim_risk_level": "risk_levels",
        "dim_metric": "metrics",
        "dim_investment_term": "investment_terms",
    }
    return mapping.get(table, "")


def _table_label(table: str) -> str:
    mapping = {
        "dim_account": "账户",
        "dim_category": "类别",
        "dim_source_type": "来源类型",
        "dim_action_type": "动作类型",
        "dim_product_type": "产品类型",
        "dim_risk_level": "风险等级",
        "dim_metric": "指标类型",
        "dim_investment_term": "投资期限",
    }
    return mapping.get(table, "主数据")
