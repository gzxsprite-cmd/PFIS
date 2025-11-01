from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ... import crud
from ...database import get_db
from ...schemas import ProductMasterCreate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _load_master(db: Session):
    master = crud.list_master_data(db)
    return {
        "product_types": master.get("product_types", []),
        "risk_levels": master.get("risk_levels", []),
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


@router.get("/products/form", response_class=HTMLResponse)
async def form(request: Request, db: Session = Depends(get_db)):
    master = _load_master(db)
    return templates.TemplateResponse(
        "product_tracker/products/form.html",
        {"request": request, "master": master},
    )


@router.post("/products", response_class=HTMLResponse)
async def create_product(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    type_id: Optional[int] = Form(default=None),
    risk_level_id: Optional[int] = Form(default=None),
    launch_date: Optional[str] = Form(default=None),
    remark: Optional[str] = Form(default=None),
):
    payload = ProductMasterCreate(
        name=name,
        type_id=type_id,
        risk_level_id=risk_level_id,
        launch_date=date.fromisoformat(launch_date) if launch_date else None,
        remark=remark or None,
    )
    crud.add_product(db, payload)
    return _render_table(request, db)


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
