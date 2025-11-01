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
    channel_id: Optional[int] = None
    remark: Optional[str] = None


class ProductMasterCreate(BaseModel):
    product_name: str
    type_id: Optional[int] = None
    risk_level_id: Optional[int] = None
    launch_date: Optional[date] = None
    remark: Optional[str] = None
    is_active: bool = True


class ProductMetricsCreate(BaseModel):
    product_id: int
    record_date: date
    metric_1: Optional[float] = None
    metric_2: Optional[float] = None
    metric_3: Optional[float] = None
    source: Optional[str] = None
    remark: Optional[str] = None


class MasterDataCreate(BaseModel):
    table: str
    name: str
