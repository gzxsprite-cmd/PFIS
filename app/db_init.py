from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from .database import Base, SessionLocal, engine
from . import models


MASTER_DEFAULTS = {
    models.DimAccount: ["现金账户", "银行卡", "证券账户"],
    models.DimCategory: ["工资收入", "生活支出", "投资转出", "投资回流"],
    models.DimProductType: ["货币基金", "股票基金", "债券"],
    models.DimRiskLevel: ["低", "中", "高"],
    models.DimActionType: ["买入", "赎回", "分红"],
    models.DimSourceType: ["工资", "理财", "其他"],
}


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        for model_cls, names in MASTER_DEFAULTS.items():
            for name in names:
                instance = model_cls(name=name)
                session.add(instance)
                try:
                    session.commit()
                except IntegrityError:
                    session.rollback()
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
    print("✅ 数据库初始化完成")
