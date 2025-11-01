from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..schemas import CashFlowCreate

router = APIRouter(prefix="/cashflow", tags=["Cash Flow"])
templates = Jinja2Templates(directory="app/templates")
UPLOAD_DIR = Path("app/static/uploads/ocr_pending")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("", response_class=HTMLResponse)
async def cashflow_list(request: Request, db: Session = Depends(get_db)):
    cashflows = crud.list_cash_flows(db)
    master_data = crud.list_master_data(db)
    return templates.TemplateResponse(
        "cash_flow/list.html",
        {
            "request": request,
            "cashflows": cashflows,
            "master_data": master_data,
        },
    )


@router.get("/form", response_class=HTMLResponse)
async def cashflow_form(request: Request, db: Session = Depends(get_db)):
    master_data = crud.list_master_data(db)
    return templates.TemplateResponse(
        "cash_flow/form.html",
        {
            "request": request,
            "master_data": master_data,
        },
    )


@router.post("/add", response_class=HTMLResponse)
async def cashflow_add(
    request: Request,
    db: Session = Depends(get_db),
    date_value: str = Form(...),
    account_id: str = Form(...),
    category_id: Optional[str] = Form(default=None),
    flow_type: str = Form(...),
    amount: str = Form(...),
    source_type_id: Optional[str] = Form(default=None),
    remark: Optional[str] = Form(default=None),
    receipt: Optional[UploadFile] = File(default=None),
):
    payload = CashFlowCreate(
        date=date.fromisoformat(date_value),
        account_id=int(account_id),
        category_id=int(category_id) if category_id else None,
        flow_type=flow_type,
        amount=float(amount),
        source_type_id=int(source_type_id) if source_type_id else None,
        remark=remark or None,
    )
    crud.create_cash_flow(db, payload)

    if receipt and receipt.filename:
        filename = f"cashflow_{uuid4().hex}_{receipt.filename}"
        file_path = UPLOAD_DIR / filename
        file_bytes = await receipt.read()
        file_path.write_bytes(file_bytes)
        crud.add_ocr_entry(db, "cashflow", f"/static/uploads/ocr_pending/{filename}")

    cashflows = crud.list_cash_flows(db)
    return templates.TemplateResponse(
        "cash_flow/table.html",
        {
            "request": request,
            "cashflows": cashflows,
        },
    )
