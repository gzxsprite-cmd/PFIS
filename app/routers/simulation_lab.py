from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db

router = APIRouter(prefix="/simulation", tags=["Simulation Lab"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def simulation_home(request: Request, db: Session = Depends(get_db)):
    products = crud.list_products(db)
    return templates.TemplateResponse(
        "simulation_lab.html",
        {
            "request": request,
            "products": products,
        },
    )


@router.post("/calc", response_class=HTMLResponse)
async def simulation_calc(
    request: Request,
    db: Session = Depends(get_db),
    product_id: str = Form(...),
    amount: str = Form(...),
    expected_days: str = Form(...),
):
    product = crud.get_product(db, int(product_id))
    invest_amount = float(amount)
    days = int(expected_days)
    annual_yield = 0.035
    if product and product.holding:
        annual_yield = max(product.holding.avg_yield, 0.02)
    est_profit = invest_amount * annual_yield * days / 365
    context = {
        "request": request,
        "product": product,
        "amount": invest_amount,
        "days": days,
        "annual_yield": annual_yield,
        "est_profit": est_profit,
    }
    return templates.TemplateResponse("partials/simulation_result.html", context)
