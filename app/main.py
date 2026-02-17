from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .db_init import init_db
from .routers import (
    cash_flow,
    dashboard,
    data_tools,
    investment_log,
    master_data,
    ocr_pending,
    product_tracker,
    simulation_lab,
)

app = FastAPI(title="Personal Finance & Investment System")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

app.include_router(dashboard.router)
app.include_router(cash_flow.router)
app.include_router(investment_log.router)
app.include_router(product_tracker.router)
app.include_router(master_data.router)
app.include_router(simulation_lab.router)
app.include_router(ocr_pending.router)
app.include_router(data_tools.router)


@app.on_event("startup")
async def startup_event():
    init_db()
