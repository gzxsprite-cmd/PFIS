from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class CashFlowCreate(BaseModel):
    date: date
    account_id: int
    category_id: Optional[int] = None
    flow_type: str = Field(pattern="^(收入|支出)$")
    amount: float
    source_type_id: Optional[int] = None
    remark: Optional[str] = None
    link_investment_id: Optional[int] = None


class InvestmentLogCreate(BaseModel):
    date: date
    product_id: int
    action_id: int
    amount: float
    channel_account_id: Optional[int] = None
    remark: Optional[str] = None
    cashflow_link_id: Optional[int] = None


class ProductMasterCreate(BaseModel):
    name: str
    type_id: Optional[int] = None
    risk_level_id: Optional[int] = None
    launch_date: Optional[date] = None
    remark: Optional[str] = None
    status: str = "active"


class ProductMetricCreate(BaseModel):
    product_id: int
    metric_id: int
    record_date: date
    value: float
    source: Optional[str] = None
    remark: Optional[str] = None


class MasterDataCreate(BaseModel):
    table: str
    name: str
