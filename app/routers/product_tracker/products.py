from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ... import crud
from ...database import get_db
from ...schemas import ProductMasterCreate
from ...utils import encode_header_value

SELECT_BASE_CLASS = (
    "w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm "
    "focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _load_master(db: Session):
    master = crud.list_master_data(db)
    return {
        "product_types": master.get("product_types", []),
        "risk_levels": master.get("risk_levels", []),
        "investment_terms": master.get("investment_terms", []),
    }


def _render_table(request: Request, db: Session) -> HTMLResponse:
    products = crud.list_products(db, include_inactive=True)
    return templates.TemplateResponse(
        "product_tracker/products/table.html",
        {"request": request, "products": products},
    )


@router.get("/products", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    products = crud.list_products(db, include_inactive=True)
    master = _load_master(db)
    return templates.TemplateResponse(
        "product_tracker/products/index.html",
        {
            "request": request,
            "products": products,
            "master": master,
        },
    )


@router.get("/products/add_form", response_class=HTMLResponse)
async def add_form(request: Request, db: Session = Depends(get_db)):
    master = _load_master(db)
    return templates.TemplateResponse(
        "partials/_edit_modal.html",
        {
            "request": request,
            "title": "新增理财产品",
            "form_action": "/product_tracker/products",
            "form_template": "product_tracker/products/_form_fields.html",
            "hx_target": "#product-table",
            "hx_swap": "innerHTML",
            "master": master,
            "form_id": "product-new",
            "submit_label": "保存",
        },
    )


@router.get("/products/quick_form", response_class=HTMLResponse)
async def quick_form(
    request: Request,
    field_id: str = Query(...),
    field_name: str = Query(...),
    include_blank: bool = Query(False),
    blank_label: str = Query("---"),
    db: Session = Depends(get_db),
):
    master = _load_master(db)
    return templates.TemplateResponse(
        "partials/_edit_modal.html",
        {
            "request": request,
            "title": "新增理财产品",
            "form_action": "/product_tracker/products",
            "form_template": "product_tracker/products/_form_fields.html",
            "hx_target": f"#{field_id}",
            "hx_swap": "outerHTML",
            "master": master,
            "form_id": f"product-quick-{field_id}",
            "submit_label": "保存",
            "target_select_id": field_id,
            "target_field_name": field_name,
            "include_blank": include_blank,
            "blank_label": blank_label,
        },
    )


@router.post("/products", response_class=HTMLResponse)
async def create_product(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    type_id: Optional[int] = Form(default=None),
    risk_level_id: Optional[int] = Form(default=None),
    investment_term_id: Optional[int] = Form(default=None),
    launch_date: Optional[str] = Form(default=None),
    remark: Optional[str] = Form(default=None),
    target_select_id: Optional[str] = Form(default=None),
    target_field_name: Optional[str] = Form(default=None),
    include_blank: str = Form("false"),
    blank_label: str = Form("---"),
):
    payload = ProductMasterCreate(
        name=name,
        type_id=type_id,
        risk_level_id=risk_level_id,
        investment_term_id=investment_term_id,
        launch_date=date.fromisoformat(launch_date) if launch_date else None,
        remark=remark or None,
    )
    product = crud.add_product(db, payload)
    if target_select_id and target_field_name:
        products = crud.list_products(db)
        response = templates.TemplateResponse(
            "partials/master_select.html",
            {
                "request": request,
                "items": products,
                "field_id": target_select_id,
                "field_name": target_field_name,
                "selected_id": product.id,
                "include_blank": include_blank.lower() == "true",
                "blank_label": blank_label or "---",
                "select_classes": SELECT_BASE_CLASS,
            },
        )
        response.headers["HX-Toast"] = encode_header_value("理财产品已新增")
        return response
    response = _render_table(request, db)
    response.headers["HX-Toast"] = encode_header_value("理财产品已新增")
    return response


@router.get("/products/{product_id}/edit", response_class=HTMLResponse)
async def edit_product(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    master = _load_master(db)
    return templates.TemplateResponse(
        "partials/_edit_modal.html",
        {
            "request": request,
            "title": "编辑理财产品",
            "form_action": f"/product_tracker/products/{product_id}",
            "form_template": "product_tracker/products/_form_fields.html",
            "hx_target": "#product-table",
            "hx_swap": "innerHTML",
            "master": master,
            "item": product,
            "show_status": True,
            "form_id": f"product-{product_id}",
        },
    )


@router.post("/products/{product_id}", response_class=HTMLResponse)
async def update_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    name: str = Form(...),
    type_id: Optional[int] = Form(default=None),
    risk_level_id: Optional[int] = Form(default=None),
    investment_term_id: Optional[int] = Form(default=None),
    launch_date: Optional[str] = Form(default=None),
    remark: Optional[str] = Form(default=None),
    status: str = Form(default="active"),
):
    payload = ProductMasterCreate(
        name=name,
        type_id=type_id,
        risk_level_id=risk_level_id,
        investment_term_id=investment_term_id,
        launch_date=date.fromisoformat(launch_date) if launch_date else None,
        remark=remark or None,
        status=status,
    )
    product = crud.update_product(db, product_id, payload, status=status)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    response = _render_table(request, db)
    response.headers["HX-Toast"] = encode_header_value("理财产品已更新")
    return response


@router.post("/products/{product_id}/status", response_class=HTMLResponse)
async def update_status(
    request: Request,
    product_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    product = crud.update_product_status(db, product_id, status)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _render_table(request, db)
