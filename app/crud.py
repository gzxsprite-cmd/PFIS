from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from . import models
from .schemas import (
    CashFlowCreate,
    InvestmentLogCreate,
    MasterDataCreate,
    ProductMasterCreate,
    ProductMetricCreate,
)

MASTER_TABLES = {
    "dim_account": models.DimAccount,
    "dim_category": models.DimCategory,
    "dim_source_type": models.DimSourceType,
    "dim_action_type": models.DimActionType,
    "dim_product_type": models.DimProductType,
    "dim_risk_level": models.DimRiskLevel,
    "dim_metric": models.DimMetric,
}

MASTER_OVERVIEW = {
    "accounts": models.DimAccount,
    "categories": models.DimCategory,
    "source_types": models.DimSourceType,
    "action_types": models.DimActionType,
    "product_types": models.DimProductType,
    "risk_levels": models.DimRiskLevel,
    "metrics": models.DimMetric,
}


def list_master_data(db: Session, include_inactive: bool = False) -> Dict[str, List[models.Base]]:
    result: Dict[str, List] = {}
    for key, model in MASTER_OVERVIEW.items():
        query = select(model).order_by(model.name)
        if not include_inactive and hasattr(model, "status"):
            query = query.where(model.status == "active")
        result[key] = list(db.execute(query).scalars())
    return result


def create_master_data(db: Session, payload: MasterDataCreate) -> models.Base:
    model_cls = MASTER_TABLES.get(payload.table)
    if not model_cls:
        raise ValueError("Unsupported master table")
    instance = model_cls(name=payload.name)
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def toggle_master_status(db: Session, table: str, row_id: int, status: str) -> Optional[models.Base]:
    model_cls = MASTER_TABLES.get(table)
    if not model_cls:
        raise ValueError("Unsupported master table")
    instance = db.get(model_cls, row_id)
    if not instance:
        return None
    if hasattr(instance, "status"):
        setattr(instance, "status", status)
        db.commit()
        db.refresh(instance)
    return instance


def master_impact(db: Session, table: str, row_id: int) -> List[Dict[str, int]]:
    impact_map = {
        "dim_account": [
            (models.CashFlow, models.CashFlow.account_id),
            (models.InvestmentLog, models.InvestmentLog.channel_account_id),
        ],
        "dim_category": [(models.CashFlow, models.CashFlow.category_id)],
        "dim_source_type": [(models.CashFlow, models.CashFlow.source_type_id)],
        "dim_action_type": [(models.InvestmentLog, models.InvestmentLog.action_id)],
        "dim_product_type": [(models.ProductMaster, models.ProductMaster.type_id)],
        "dim_risk_level": [(models.ProductMaster, models.ProductMaster.risk_level_id)],
        "dim_metric": [(models.ProductMetric, models.ProductMetric.metric_id)],
    }
    checks = impact_map.get(table, [])
    response: List[Dict[str, int]] = []
    for model, column in checks:
        count_stmt = select(func.count()).where(column == row_id)
        count = db.execute(count_stmt).scalar_one()
        if count:
            response.append({"table": model.__tablename__, "count": count})
    return response


def list_cash_flows(db: Session, include_inactive: bool = False) -> List[models.CashFlow]:
    stmt = (
        select(models.CashFlow)
        .order_by(models.CashFlow.date.desc(), models.CashFlow.id.desc())
    )
    if not include_inactive:
        stmt = stmt.where(models.CashFlow.status == "active")
    return list(db.execute(stmt).scalars())


def create_cash_flow(db: Session, payload: CashFlowCreate) -> models.CashFlow:
    cash_flow = models.CashFlow(**payload.dict())
    db.add(cash_flow)
    db.commit()
    db.refresh(cash_flow)
    return cash_flow


def soft_delete_cashflow(db: Session, record_id: int) -> Optional[models.CashFlow]:
    cash_flow = db.get(models.CashFlow, record_id)
    if not cash_flow:
        return None
    cash_flow.status = "inactive"
    db.commit()
    db.refresh(cash_flow)
    return cash_flow


def list_investments(db: Session, include_inactive: bool = False) -> List[models.InvestmentLog]:
    stmt = (
        select(models.InvestmentLog)
        .order_by(models.InvestmentLog.date.desc(), models.InvestmentLog.id.desc())
    )
    if not include_inactive:
        stmt = stmt.where(models.InvestmentLog.status == "active")
    return list(db.execute(stmt).scalars())


def create_investment(db: Session, payload: InvestmentLogCreate) -> models.InvestmentLog:
    investment = models.InvestmentLog(**payload.dict())
    db.add(investment)
    db.commit()
    db.refresh(investment)
    return investment


def soft_delete_investment(db: Session, record_id: int) -> Optional[models.InvestmentLog]:
    record = db.get(models.InvestmentLog, record_id)
    if not record:
        return None
    record.status = "inactive"
    db.commit()
    db.refresh(record)
    return record


def list_products(db: Session, include_inactive: bool = False) -> List[models.ProductMaster]:
    stmt = select(models.ProductMaster).order_by(models.ProductMaster.name)
    if not include_inactive:
        stmt = stmt.where(models.ProductMaster.status == "active")
    return list(db.execute(stmt).scalars())


def get_product(db: Session, product_id: int) -> Optional[models.ProductMaster]:
    return db.get(models.ProductMaster, product_id)


def add_product(db: Session, payload: ProductMasterCreate) -> models.ProductMaster:
    product = models.ProductMaster(**payload.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product_status(db: Session, product_id: int, status: str) -> Optional[models.ProductMaster]:
    product = db.get(models.ProductMaster, product_id)
    if not product:
        return None
    product.status = status
    db.commit()
    db.refresh(product)
    return product


def add_product_metric(db: Session, payload: ProductMetricCreate) -> models.ProductMetric:
    metric = models.ProductMetric(**payload.dict())
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


def list_metrics(
    db: Session,
    product_id: Optional[int] = None,
    metric_id: Optional[int] = None,
    limit: int = 50,
) -> List[models.ProductMetric]:
    stmt = select(models.ProductMetric).order_by(models.ProductMetric.record_date.desc())
    if product_id:
        stmt = stmt.where(models.ProductMetric.product_id == product_id)
    if metric_id:
        stmt = stmt.where(models.ProductMetric.metric_id == metric_id)
    stmt = stmt.limit(limit)
    return list(db.execute(stmt).scalars())


def list_ocr_pending(db: Session) -> List[models.OcrPending]:
    stmt = select(models.OcrPending).order_by(models.OcrPending.created_at.desc())
    return list(db.execute(stmt).scalars())


def add_ocr_entry(db: Session, module: str, path: str) -> models.OcrPending:
    entry = models.OcrPending(module=module, image_path=path)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def analytics_summary(db: Session) -> Dict[str, float]:
    summary = defaultdict(float)

    income_stmt = select(func.coalesce(func.sum(models.CashFlow.amount), 0)).where(
        models.CashFlow.flow_type == "收入",
        models.CashFlow.status == "active",
    )
    expense_stmt = select(func.coalesce(func.sum(models.CashFlow.amount), 0)).where(
        models.CashFlow.flow_type == "支出",
        models.CashFlow.status == "active",
    )
    investment_stmt = select(func.coalesce(func.sum(models.InvestmentLog.amount), 0)).where(
        models.InvestmentLog.status == "active"
    )

    summary["total_income"] = db.execute(income_stmt).scalar_one()
    summary["total_expense"] = db.execute(expense_stmt).scalar_one()
    summary["total_invested"] = db.execute(investment_stmt).scalar_one()
    summary["net_cash"] = summary["total_income"] - summary["total_expense"]
    return dict(summary)


def monthly_cashflow(db: Session) -> List[Tuple[str, float]]:
    stmt = (
        select(
            func.strftime("%Y-%m", models.CashFlow.date),
            func.sum(
                case(
                    (models.CashFlow.flow_type == "收入", models.CashFlow.amount),
                    else_=-models.CashFlow.amount,
                )
            ),
        )
        .where(models.CashFlow.status == "active")
        .group_by(func.strftime("%Y-%m", models.CashFlow.date))
        .order_by(func.strftime("%Y-%m", models.CashFlow.date))
    )
    return [(row[0], row[1]) for row in db.execute(stmt)]
