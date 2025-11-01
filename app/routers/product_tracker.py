from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..schemas import ProductMasterCreate, ProductMetricsCreate

router = APIRouter(prefix="/products", tags=["Products"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def product_list(request: Request, db: Session = Depends(get_db)):
    products = crud.list_products(db)
    master_data = crud.list_master_data(db)
    return templates.TemplateResponse(
        "product_tracker/list.html",
        {
            "request": request,
            "products": products,
            "master_data": master_data,
        },
    )


@router.post("/add", response_class=HTMLResponse)
async def product_add(
    request: Request,
    db: Session = Depends(get_db),
    product_name: str = Form(...),
    type_id: str | None = Form(default=None),
    risk_level_id: str | None = Form(default=None),
    launch_date: str | None = Form(default=None),
    remark: str | None = Form(default=None),
):
    payload = ProductMasterCreate(
        product_name=product_name,
        type_id=int(type_id) if type_id else None,
        risk_level_id=int(risk_level_id) if risk_level_id else None,
        launch_date=date.fromisoformat(launch_date) if launch_date else None,
        remark=remark or None,
    )
    crud.add_product(db, payload)
    products = crud.list_products(db)
    master_data = crud.list_master_data(db)
    return templates.TemplateResponse(
        "product_tracker/table.html",
        {
            "request": request,
            "products": products,
            "master_data": master_data,
        },
    )


@router.get("/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    metrics = list(reversed(crud.recent_metrics(db, product_id, limit=24)))
    chart_data = {
        "dates": [m.record_date.isoformat() for m in metrics],
        "values": [m.metric_1 or 0 for m in metrics],
    }
    return templates.TemplateResponse(
        "product_tracker/detail.html",
        {
            "request": request,
            "product": product,
            "metrics": metrics,
            "chart_data": json.dumps(chart_data),
        },
    )


@router.post("/{product_id}/metrics", response_class=HTMLResponse)
async def add_metric(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db),
    record_date: str = Form(...),
    metric_1: str | None = Form(default=None),
    metric_2: str | None = Form(default=None),
    metric_3: str | None = Form(default=None),
    source: str | None = Form(default=None),
    remark: str | None = Form(default=None),
):
    payload = ProductMetricsCreate(
        product_id=product_id,
        record_date=date.fromisoformat(record_date),
        metric_1=float(metric_1) if metric_1 else None,
        metric_2=float(metric_2) if metric_2 else None,
        metric_3=float(metric_3) if metric_3 else None,
        source=source or None,
        remark=remark or None,
    )
    crud.add_product_metric(db, payload)
    return await product_detail(request, product_id, db)
