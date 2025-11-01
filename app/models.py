from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class StatusMixin:
    status = Column(String, default="active", nullable=False)


class DimAccount(Base, StatusMixin):
    __tablename__ = "dim_account"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)

    cash_flows = relationship("CashFlow", back_populates="account")
    investment_logs = relationship("InvestmentLog", back_populates="channel_account")


class DimCategory(Base, StatusMixin):
    __tablename__ = "dim_category"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("dim_category.id"))

    parent = relationship("DimCategory", remote_side=[id])
    cash_flows = relationship("CashFlow", back_populates="category")


class DimSourceType(Base, StatusMixin):
    __tablename__ = "dim_source_type"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    cash_flows = relationship("CashFlow", back_populates="source_type")


class DimActionType(Base, StatusMixin):
    __tablename__ = "dim_action_type"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    investment_logs = relationship("InvestmentLog", back_populates="action")


class DimProductType(Base, StatusMixin):
    __tablename__ = "dim_product_type"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    products = relationship("ProductMaster", back_populates="product_type")


class DimRiskLevel(Base, StatusMixin):
    __tablename__ = "dim_risk_level"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)

    products = relationship("ProductMaster", back_populates="risk_level")


class DimMetric(Base, StatusMixin):
    __tablename__ = "dim_metric"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    unit = Column(String)
    description = Column(Text)

    metrics = relationship("ProductMetric", back_populates="metric")


class CashFlow(Base):
    __tablename__ = "cash_flow"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=date.today, nullable=False)
    account_id = Column(Integer, ForeignKey("dim_account.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("dim_category.id"))
    flow_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    source_type_id = Column(Integer, ForeignKey("dim_source_type.id"))
    remark = Column(String)
    status = Column(String, default="active", nullable=False)
    link_investment_id = Column(Integer, ForeignKey("investment_log.id"))

    account = relationship("DimAccount", back_populates="cash_flows")
    category = relationship("DimCategory", back_populates="cash_flows")
    source_type = relationship("DimSourceType", back_populates="cash_flows")
    investment = relationship(
        "InvestmentLog",
        foreign_keys=[link_investment_id],
        uselist=False,
        overlaps="cashflow_link",
    )


class ProductMaster(Base):
    __tablename__ = "product_master"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    type_id = Column(Integer, ForeignKey("dim_product_type.id"))
    risk_level_id = Column(Integer, ForeignKey("dim_risk_level.id"))
    launch_date = Column(Date)
    remark = Column(Text)
    status = Column(String, default="active", nullable=False)

    product_type = relationship("DimProductType", back_populates="products")
    risk_level = relationship("DimRiskLevel", back_populates="products")
    metrics = relationship(
        "ProductMetric",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    holding = relationship("HoldingStatus", back_populates="product", uselist=False)
    investments = relationship("InvestmentLog", back_populates="product")


class InvestmentLog(Base):
    __tablename__ = "investment_log"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=date.today, nullable=False)
    product_id = Column(Integer, ForeignKey("product_master.id"), nullable=False)
    action_id = Column(Integer, ForeignKey("dim_action_type.id"), nullable=False)
    amount = Column(Float, nullable=False)
    channel_account_id = Column(Integer, ForeignKey("dim_account.id"))
    remark = Column(Text)
    status = Column(String, default="active", nullable=False)
    cashflow_link_id = Column(Integer, ForeignKey("cash_flow.id"))

    product = relationship("ProductMaster", back_populates="investments")
    action = relationship("DimActionType", back_populates="investment_logs")
    channel_account = relationship("DimAccount", back_populates="investment_logs")
    cashflow_link = relationship(
        "CashFlow",
        foreign_keys=[cashflow_link_id],
        uselist=False,
        overlaps="investment",
    )


class ProductMetric(Base):
    __tablename__ = "product_metrics"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product_master.id"), nullable=False)
    metric_id = Column(Integer, ForeignKey("dim_metric.id"), nullable=False)
    record_date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    source = Column(String)
    remark = Column(Text)

    product = relationship("ProductMaster", back_populates="metrics")
    metric = relationship("DimMetric", back_populates="metrics")


class HoldingStatus(Base):
    __tablename__ = "holding_status"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product_master.id"), nullable=False)
    total_invest = Column(Float, default=0)
    est_profit = Column(Float, default=0)
    avg_yield = Column(Float, default=0)
    last_update = Column(Date)

    product = relationship("ProductMaster", back_populates="holding")


class OcrPending(Base):
    __tablename__ = "ocr_pending"

    id = Column(Integer, primary_key=True, index=True)
    module = Column(String, nullable=False)
    image_path = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    remark = Column(Text)
