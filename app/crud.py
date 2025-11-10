from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from . import models
from .schemas import (
    CashFlowCreate,
    InvestmentLogCreate,
    MasterDataCreate,
    ProductMasterCreate,
    ProductMetricCreate,
)

INCOME_TYPES = {"收入", "income", "Income", "INCOME"}
EXPENSE_TYPES = {"支出", "expense", "Expense", "EXPENSE"}
BUY_ACTION_TYPES = {
    "买入",
    "申购",
    "加仓",
    "购买",
    "buy",
    "Buy",
    "BUY",
    "purchase",
    "Purchase",
    "PURCHASE",
}
BUY_ACTION_TYPES_LOWER = {name.lower() for name in BUY_ACTION_TYPES}

def _is_active(column):
    """Treat NULL or empty status as active for legacy rows."""

    return or_(column == "active", column.is_(None), column == "")

MASTER_TABLES = {
    "dim_account": models.DimAccount,
    "dim_category": models.DimCategory,
    "dim_source_type": models.DimSourceType,
    "dim_action_type": models.DimActionType,
    "dim_product_type": models.DimProductType,
    "dim_risk_level": models.DimRiskLevel,
    "dim_metric": models.DimMetric,
    "dim_investment_term": models.DimInvestmentTerm,
}

MASTER_OVERVIEW = {
    "accounts": models.DimAccount,
    "categories": models.DimCategory,
    "source_types": models.DimSourceType,
    "action_types": models.DimActionType,
    "product_types": models.DimProductType,
    "risk_levels": models.DimRiskLevel,
    "metrics": models.DimMetric,
    "investment_terms": models.DimInvestmentTerm,
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


def get_master_item(db: Session, table: str, row_id: int) -> Optional[models.Base]:
    model_cls = MASTER_TABLES.get(table)
    if not model_cls:
        return None
    return db.get(model_cls, row_id)


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
        "dim_investment_term": [
            (models.ProductMaster, models.ProductMaster.investment_term_id)
        ],
    }
    checks = impact_map.get(table, [])
    response: List[Dict[str, int]] = []
    for model, column in checks:
        count_stmt = select(func.count()).where(column == row_id)
        count = db.execute(count_stmt).scalar_one()
        if count:
            response.append({"table": model.__tablename__, "count": count})
    return response


def soft_delete_master(db: Session, table: str, row_id: int) -> Optional[models.Base]:
    model_cls = MASTER_TABLES.get(table)
    if not model_cls:
        return None
    instance = db.get(model_cls, row_id)
    if not instance or not hasattr(instance, "status"):
        return instance
    instance.status = "inactive"
    db.commit()
    db.refresh(instance)
    return instance


def list_active_master_options(db: Session, table: str) -> List[models.Base]:
    model_cls = MASTER_TABLES.get(table)
    if not model_cls:
        return []
    stmt = select(model_cls).order_by(model_cls.name)
    if hasattr(model_cls, "status"):
        stmt = stmt.where(model_cls.status == "active")
    return list(db.execute(stmt).scalars())


def list_cash_flows(db: Session, include_inactive: bool = False) -> List[models.CashFlow]:
    stmt = (
        select(models.CashFlow)
        .order_by(models.CashFlow.date.desc(), models.CashFlow.id.desc())
    )
    if not include_inactive:
        stmt = stmt.where(models.CashFlow.status == "active")
    return list(db.execute(stmt).scalars())


def get_cash_flow(db: Session, record_id: int) -> Optional[models.CashFlow]:
    return db.get(models.CashFlow, record_id)


def create_cash_flow(db: Session, payload: CashFlowCreate) -> models.CashFlow:
    cash_flow = models.CashFlow(**payload.dict())
    db.add(cash_flow)
    db.commit()
    db.refresh(cash_flow)
    return cash_flow


def update_cash_flow(db: Session, record_id: int, payload: CashFlowCreate) -> Optional[models.CashFlow]:
    cash_flow = db.get(models.CashFlow, record_id)
    if not cash_flow:
        return None
    for field, value in payload.dict().items():
        setattr(cash_flow, field, value)
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


def get_investment(db: Session, record_id: int) -> Optional[models.InvestmentLog]:
    return db.get(models.InvestmentLog, record_id)


def create_investment(db: Session, payload: InvestmentLogCreate) -> models.InvestmentLog:
    investment = models.InvestmentLog(**payload.dict())
    db.add(investment)
    db.commit()
    db.refresh(investment)
    return investment


def update_investment(db: Session, record_id: int, payload: InvestmentLogCreate) -> Optional[models.InvestmentLog]:
    investment = db.get(models.InvestmentLog, record_id)
    if not investment:
        return None
    for field, value in payload.dict().items():
        setattr(investment, field, value)
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


def update_product(
    db: Session,
    product_id: int,
    payload: ProductMasterCreate,
    *,
    status: Optional[str] = None,
) -> Optional[models.ProductMaster]:
    product = db.get(models.ProductMaster, product_id)
    if not product:
        return None
    for field, value in payload.dict().items():
        setattr(product, field, value)
    if status:
        product.status = status
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


def get_metric(db: Session, record_id: int) -> Optional[models.ProductMetric]:
    return db.get(models.ProductMetric, record_id)


def update_product_metric(
    db: Session, record_id: int, payload: ProductMetricCreate
) -> Optional[models.ProductMetric]:
    metric = db.get(models.ProductMetric, record_id)
    if not metric:
        return None
    for field, value in payload.dict().items():
        setattr(metric, field, value)
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
        models.CashFlow.flow_type.in_(INCOME_TYPES),
        _is_active(models.CashFlow.status),
    )
    expense_stmt = select(func.coalesce(func.sum(models.CashFlow.amount), 0)).where(
        models.CashFlow.flow_type.in_(EXPENSE_TYPES),
        _is_active(models.CashFlow.status),
    )
    investment_stmt = select(func.coalesce(func.sum(models.InvestmentLog.amount), 0)).where(
        _is_active(models.InvestmentLog.status)
    )

    summary["total_income"] = db.execute(income_stmt).scalar_one()
    summary["total_expense"] = db.execute(expense_stmt).scalar_one()
    summary["total_invested"] = db.execute(investment_stmt).scalar_one()
    summary["net_cash"] = summary["total_income"] - summary["total_expense"]
    return dict(summary)


def monthly_cashflow(db: Session) -> List[Dict[str, Any]]:
    cashflow_month = func.strftime("%Y-%m", models.CashFlow.date)
    income_stmt = (
        select(cashflow_month.label("month"), func.coalesce(func.sum(models.CashFlow.amount), 0))
        .where(
            _is_active(models.CashFlow.status),
            models.CashFlow.flow_type.in_(INCOME_TYPES),
        )
        .group_by(cashflow_month)
    )
    expense_stmt = (
        select(cashflow_month.label("month"), func.coalesce(func.sum(models.CashFlow.amount), 0))
        .where(
            _is_active(models.CashFlow.status),
            models.CashFlow.flow_type.in_(EXPENSE_TYPES),
        )
        .group_by(cashflow_month)
    )
    invest_month = func.strftime("%Y-%m", models.InvestmentLog.date)
    invest_stmt = (
        select(
            invest_month.label("month"),
            func.coalesce(
                func.sum(
                    case(
                        (models.InvestmentLog.amount > 0, models.InvestmentLog.amount),
                        else_=0.0,
                    )
                ),
                0,
            ),
        )
        .join(models.DimActionType, models.InvestmentLog.action)
        .where(
            _is_active(models.InvestmentLog.status),
            or_(
                models.DimActionType.name.in_(BUY_ACTION_TYPES),
                func.lower(models.DimActionType.name).in_(BUY_ACTION_TYPES_LOWER),
            ),
        )
        .group_by(invest_month)
    )

    income_map = {row.month: float(row[1] or 0) for row in db.execute(income_stmt)}
    expense_map = {row.month: float(row[1] or 0) for row in db.execute(expense_stmt)}
    invest_map = {row.month: float(row[1] or 0) for row in db.execute(invest_stmt)}

    all_months = sorted(set(income_map) | set(expense_map) | set(invest_map))
    results: List[Dict[str, Any]] = []
    running_net = 0.0
    for month in all_months:
        income = income_map.get(month, 0.0)
        expense = expense_map.get(month, 0.0)
        invested = invest_map.get(month, 0.0)
        ratio = invested / income if income else 0.0
        net_cash = income - expense
        running_net += net_cash
        results.append(
            {
                "month": month,
                "income": income,
                "expense": expense,
                "investment": invested,
                "investment_ratio": ratio,
                "net_cash": net_cash,
                "cumulative_net_cash": running_net,
            }
        )
    return results


def update_master_data(
    db: Session,
    table: str,
    row_id: int,
    *,
    name: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[models.Base]:
    instance = get_master_item(db, table, row_id)
    if not instance:
        return None
    if name is not None:
        setattr(instance, "name", name)
    if status is not None and hasattr(instance, "status"):
        setattr(instance, "status", status)
    db.commit()
    db.refresh(instance)
    return instance
