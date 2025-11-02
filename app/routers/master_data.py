from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Path, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..schemas import MasterDataCreate

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
    return templates.TemplateResponse(
        "master_data/table.html",
        {
            "request": request,
            "table": table,
            "items": master_data.get(_table_key(table), []),
        },
    )


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
    response.headers["HX-Toast"] = "主数据已更新"
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


@router.get("/impact/{table}/{item_id}")
async def impact(table: str, item_id: int, db: Session = Depends(get_db)):
    data = crud.master_impact(db, table, item_id)
    return JSONResponse({"impact": data})


def _table_key(table: str) -> str:
    mapping = {
        "dim_account": "accounts",
        "dim_category": "categories",
        "dim_source_type": "source_types",
        "dim_action_type": "action_types",
        "dim_product_type": "product_types",
        "dim_risk_level": "risk_levels",
        "dim_metric": "metrics",
    }
    return mapping.get(table, "")
