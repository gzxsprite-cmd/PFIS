from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..schemas import MasterDataCreate

router = APIRouter(prefix="/master-data", tags=["Master Data"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def master_data_home(request: Request, db: Session = Depends(get_db)):
    master_data = crud.list_master_data(db)
    return templates.TemplateResponse(
        "master_data.html",
        {
            "request": request,
            "master_data": master_data,
        },
    )


@router.post("/add", response_class=HTMLResponse)
async def master_data_add(
    request: Request,
    db: Session = Depends(get_db),
    table: str = Form(...),
    name: str = Form(...),
):
    payload = MasterDataCreate(table=table, name=name)
    try:
        crud.create_master_data(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    master_data = crud.list_master_data(db)
    table_map = {
        "dim_account": master_data.get("accounts", []),
        "dim_category": master_data.get("categories", []),
        "dim_product_type": master_data.get("product_types", []),
        "dim_risk_level": master_data.get("risk_levels", []),
        "dim_action_type": master_data.get("action_types", []),
        "dim_source_type": master_data.get("source_types", []),
    }
    return templates.TemplateResponse(
        "partials/master_data_table.html",
        {
            "request": request,
            "table": table,
            "items": table_map.get(table, []),
        },
    )


@router.get("/options/{table}", response_class=HTMLResponse)
async def master_data_options(request: Request, table: str, db: Session = Depends(get_db)):
    mapping = crud.list_master_data(db)
    table_map = {
        "dim_account": mapping.get("accounts", []),
        "dim_category": mapping.get("categories", []),
        "dim_product_type": mapping.get("product_types", []),
        "dim_risk_level": mapping.get("risk_levels", []),
        "dim_action_type": mapping.get("action_types", []),
        "dim_source_type": mapping.get("source_types", []),
    }
    if table not in table_map:
        raise HTTPException(status_code=404, detail="Unknown table")
    return templates.TemplateResponse(
        "partials/master_data_options.html",
        {
            "request": request,
            "items": table_map[table],
        },
    )
