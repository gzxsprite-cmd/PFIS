from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, List, Tuple

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from . import models
from .schemas import CashFlowCreate, InvestmentLogCreate, MasterDataCreate, ProductMasterCreate, ProductMetricsCreate


def list_master_data(db: Session) -> Dict[str, List[models.DimAccount]]:
    mapping = {
        "accounts": models.DimAccount,
        "categories": models.DimCategory,
        "product_types": models.DimProductType,
        "risk_levels": models.DimRiskLevel,
        "action_types": models.DimActionType,
        "source_types": models.DimSourceType,
    }
    result: Dict[str, List] = {}
    for key, model in mapping.items():
        result[key] = list(db.execute(select(model).order_by(model.id)).scalars())
    return result


def create_master_data(db: Session, payload: MasterDataCreate) -> models.Base:
    table_map = {
        "dim_account": models.DimAccount,
        "dim_category": models.DimCategory,
        "dim_product_type": models.DimProductType,
        "dim_risk_level": models.DimRiskLevel,
        "dim_action_type": models.DimActionType,
        "dim_source_type": models.DimSourceType,
    }
    model_cls = table_map.get(payload.table)
    if not model_cls:
        raise ValueError("Unsupported master table")
    instance = model_cls(name=payload.name)
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def list_cash_flows(db: Session):
    stmt = select(models.CashFlow).order_by(models.CashFlow.date.desc(), models.CashFlow.id.desc())
    return list(db.execute(stmt).scalars())


def create_cash_flow(db: Session, payload: CashFlowCreate) -> models.CashFlow:
    data = payload.dict()
    cash_flow = models.CashFlow(**data)
    db.add(cash_flow)
    db.commit()
    db.refresh(cash_flow)
    return cash_flow


def list_investments(db: Session):
    stmt = select(models.InvestmentLog).order_by(models.InvestmentLog.date.desc(), models.InvestmentLog.id.desc())
    return list(db.execute(stmt).scalars())


def create_investment(db: Session, payload: InvestmentLogCreate) -> models.InvestmentLog:
    investment = models.InvestmentLog(**payload.dict())
    db.add(investment)
    db.commit()
    db.refresh(investment)
    return investment


def list_products(db: Session):
    stmt = select(models.ProductMaster).order_by(models.ProductMaster.product_name)
    return list(db.execute(stmt).scalars())


def get_product(db: Session, product_id: int) -> models.ProductMaster | None:
    return db.get(models.ProductMaster, product_id)


def add_product(db: Session, payload: ProductMasterCreate) -> models.ProductMaster:
    product = models.ProductMaster(**payload.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def add_product_metric(db: Session, payload: ProductMetricsCreate) -> models.ProductMetrics:
    metric = models.ProductMetrics(**payload.dict())
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


def recent_metrics(db: Session, product_id: int, limit: int = 12) -> List[models.ProductMetrics]:
    stmt = (
        select(models.ProductMetrics)
        .where(models.ProductMetrics.product_id == product_id)
        .order_by(models.ProductMetrics.record_date.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars())


def list_ocr_pending(db: Session):
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

    income_stmt = select(func.coalesce(func.sum(models.CashFlow.amount), 0)).where(models.CashFlow.flow_type == "收入")
    expense_stmt = select(func.coalesce(func.sum(models.CashFlow.amount), 0)).where(models.CashFlow.flow_type == "支出")
    investment_stmt = select(func.coalesce(func.sum(models.InvestmentLog.amount), 0))

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
        .group_by(func.strftime("%Y-%m", models.CashFlow.date))
        .order_by(func.strftime("%Y-%m", models.CashFlow.date))
    )
    return [(row[0], row[1]) for row in db.execute(stmt)]
