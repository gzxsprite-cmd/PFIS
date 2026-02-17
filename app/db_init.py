from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from .database import Base, SessionLocal, engine
from . import models
from .migrations import run_migrations


MASTER_DEFAULTS = {
    models.DimAccount: ["现金账户", "银行卡", "证券账户"],
    models.DimCategory: ["工资收入", "生活支出", "投资转出", "投资回流"],
    models.DimProductType: ["货币基金", "股票基金", "债券"],
    models.DimRiskLevel: ["低", "中", "高"],
    models.DimActionType: ["买入", "赎回", "分红"],
    models.DimSourceType: ["工资", "理财", "其他"],
    models.DimMetric: ["净值", "收益率", "波动率"],
    models.DimInvestmentTerm: ["T+1", "T+7", "30天", "90天"],
}

REFERENCE_MAP = defaultdict(list)
REFERENCE_MAP[models.DimAccount] = [
    (models.CashFlow, models.CashFlow.account_id),
    (models.InvestmentLog, models.InvestmentLog.channel_account_id),
]
REFERENCE_MAP[models.DimCategory] = [
    (models.CashFlow, models.CashFlow.category_id),
]
REFERENCE_MAP[models.DimSourceType] = [
    (models.CashFlow, models.CashFlow.source_type_id),
]
REFERENCE_MAP[models.DimActionType] = [
    (models.InvestmentLog, models.InvestmentLog.action_id),
]
REFERENCE_MAP[models.DimProductType] = [
    (models.ProductMaster, models.ProductMaster.type_id),
]
REFERENCE_MAP[models.DimRiskLevel] = [
    (models.ProductMaster, models.ProductMaster.risk_level_id),
]
REFERENCE_MAP[models.DimMetric] = [
    (models.ProductMetric, models.ProductMetric.metric_id),
]
REFERENCE_MAP[models.DimInvestmentTerm] = [
    (models.ProductMaster, models.ProductMaster.investment_term_id),
]


def _ensure_master_defaults(session):
    """Insert default master data once and clean duplicated seed rows."""

    for model_cls, names in MASTER_DEFAULTS.items():
        stmt = (
            select(model_cls)
            .where(model_cls.name.in_(names))
            .order_by(model_cls.id)
        )
        rows = list(session.execute(stmt).scalars())
        kept = {}

        for row in rows:
            primary = kept.get(row.name)
            if primary is None:
                if hasattr(row, "status") and row.status != "active":
                    row.status = "active"
                kept[row.name] = row
                continue

            _reassign_references(session, model_cls, row.id, primary.id)
            session.delete(row)

        session.commit()

        existing_names = set(
            session.execute(
                select(model_cls.name).where(model_cls.name.in_(names))
            ).scalars()
        )

        for name in names:
            if name in existing_names:
                continue
            instance = model_cls(name=name)
            session.add(instance)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()


def _reassign_references(session, model_cls, source_id: int, target_id: int) -> None:
    mappings = REFERENCE_MAP.get(model_cls, [])
    for related_model, column in mappings:
        session.execute(
            update(related_model)
            .where(column == source_id)
            .values({column.key: target_id})
        )
    session.commit()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    session = SessionLocal()
    try:
        _ensure_master_defaults(session)
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
    print("✅ 数据库初始化完成")
