from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ... import crud
from ...database import get_db
from ...schemas import ProductMetricCreate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _chart_payload(records):
    records = sorted(records, key=lambda item: item.record_date)
    return {
        "dates": [r.record_date.isoformat() for r in records],
        "values": [r.value for r in records],
    }


def _fetch_records(db: Session, product_id: int, metric_id: int):
    return crud.list_metrics(db, product_id=product_id, metric_id=metric_id, limit=90)


@router.get("/metrics", response_class=HTMLResponse)
async def index(
    request: Request,
    product_id: Optional[int] = None,
    metric_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    master = crud.list_master_data(db)
    products = crud.list_products(db)
    metrics = master.get("metrics", [])
    if not products or not metrics:
        records = []
        chart = {"dates": [], "values": []}
        selected_product_id = product_id
        selected_metric_id = metric_id
    else:
        selected_product_id = product_id or products[0].id
        selected_metric_id = metric_id or metrics[0].id
        records = _fetch_records(db, selected_product_id, selected_metric_id)
        chart = _chart_payload(records)
    return templates.TemplateResponse(
        "product_tracker/metrics/index.html",
        {
            "request": request,
            "products": products,
            "metrics": metrics,
            "records": records,
            "selected_product_id": selected_product_id,
            "selected_metric_id": selected_metric_id,
            "chart": chart,
        },
    )


@router.get("/metrics/table", response_class=HTMLResponse)
async def table_partial(
    request: Request,
    product_id: int,
    metric_id: int,
    db: Session = Depends(get_db),
):
    records = _fetch_records(db, product_id, metric_id)
    return templates.TemplateResponse(
        "product_tracker/metrics/table.html",
        {
            "request": request,
            "records": records,
        },
    )


@router.get("/metrics/data")
async def metrics_data(
    product_id: int = Query(...),
    metric_id: int = Query(...),
    db: Session = Depends(get_db),
):
    records = _fetch_records(db, product_id, metric_id)
    return JSONResponse(_chart_payload(records))


@router.get("/metrics/form", response_class=HTMLResponse)
async def form(
    request: Request,
    product_id: Optional[int] = None,
    metric_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    master = crud.list_master_data(db)
    products = crud.list_products(db)
    return templates.TemplateResponse(
        "product_tracker/metrics/form.html",
        {
            "request": request,
            "products": products,
            "metrics": master.get("metrics", []),
            "product_id": product_id,
            "metric_id": metric_id,
        },
    )


@router.post("/metrics", response_class=HTMLResponse)
async def create_metric(
    request: Request,
    db: Session = Depends(get_db),
    product_id: int = Form(...),
    metric_id: int = Form(...),
    record_date: str = Form(...),
    value: float = Form(...),
    source: Optional[str] = Form(default=None),
    remark: Optional[str] = Form(default=None),
):
    payload = ProductMetricCreate(
        product_id=product_id,
        metric_id=metric_id,
        record_date=date.fromisoformat(record_date),
        value=value,
        source=source or None,
        remark=remark or None,
    )
    crud.add_product_metric(db, payload)
    records = _fetch_records(db, product_id, metric_id)
    return templates.TemplateResponse(
        "product_tracker/metrics/table.html",
        {
            "request": request,
            "records": records,
        },
    )


@router.get("/metrics/edit/{record_id}", response_class=HTMLResponse)
async def edit_metric(request: Request, record_id: int, db: Session = Depends(get_db)):
    record = crud.get_metric(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="指标不存在")
    master = crud.list_master_data(db)
    products = crud.list_products(db)
    return templates.TemplateResponse(
        "partials/_edit_modal.html",
        {
            "request": request,
            "title": "编辑指标记录",
            "form_action": f"/product_tracker/metrics/{record_id}",
            "form_template": "product_tracker/metrics/_form_fields.html",
            "hx_target": "#metric-table",
            "hx_swap": "outerHTML",
            "products": products,
            "metrics": master.get("metrics", []),
            "record": record,
        },
    )


@router.post("/metrics/{record_id}", response_class=HTMLResponse)
async def update_metric(
    request: Request,
    record_id: int,
    db: Session = Depends(get_db),
    product_id: int = Form(...),
    metric_id: int = Form(...),
    record_date: str = Form(...),
    value: float = Form(...),
    source: Optional[str] = Form(default=None),
    remark: Optional[str] = Form(default=None),
):
    payload = ProductMetricCreate(
        product_id=product_id,
        metric_id=metric_id,
        record_date=date.fromisoformat(record_date),
        value=value,
        source=source or None,
        remark=remark or None,
    )
    metric = crud.update_product_metric(db, record_id, payload)
    if not metric:
        raise HTTPException(status_code=404, detail="指标不存在")
    records = _fetch_records(db, product_id, metric_id)
    response = templates.TemplateResponse(
        "product_tracker/metrics/table.html",
        {
            "request": request,
            "records": records,
        },
    )
    response.headers["HX-Toast"] = "指标记录已更新"
    return response
