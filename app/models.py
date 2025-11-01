from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class DimAccount(Base):
    __tablename__ = "dim_account"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)

    cash_flows = relationship("CashFlow", back_populates="account")
    investment_logs = relationship("InvestmentLog", back_populates="channel")


class DimCategory(Base):
    __tablename__ = "dim_category"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("dim_category.id"))
    status = Column(String, default="active")

    parent = relationship("DimCategory", remote_side=[id])
    cash_flows = relationship("CashFlow", back_populates="category")


class DimProductType(Base):
    __tablename__ = "dim_product_type"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    status = Column(String, default="active")

    products = relationship("ProductMaster", back_populates="product_type")


class DimRiskLevel(Base):
    __tablename__ = "dim_risk_level"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)

    products = relationship("ProductMaster", back_populates="risk_level")


class DimActionType(Base):
    __tablename__ = "dim_action_type"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    investment_logs = relationship("InvestmentLog", back_populates="action")


class DimSourceType(Base):
    __tablename__ = "dim_source_type"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    cash_flows = relationship("CashFlow", back_populates="source_type")


class CashFlow(Base):
    __tablename__ = "cash_flow"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=date.today)
    account_id = Column(Integer, ForeignKey("dim_account.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("dim_category.id"))
    flow_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    source_type_id = Column(Integer, ForeignKey("dim_source_type.id"))
    remark = Column(String)
    link_investment_id = Column(Integer, ForeignKey("investment_log.id"))

    account = relationship("DimAccount", back_populates="cash_flows")
    category = relationship("DimCategory", back_populates="cash_flows")
    source_type = relationship("DimSourceType", back_populates="cash_flows")
    investment = relationship("InvestmentLog", back_populates="cashflow_link", uselist=False)


class ProductMaster(Base):
    __tablename__ = "product_master"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, unique=True, nullable=False)
    type_id = Column(Integer, ForeignKey("dim_product_type.id"))
    risk_level_id = Column(Integer, ForeignKey("dim_risk_level.id"))
    launch_date = Column(Date)
    remark = Column(Text)
    is_active = Column(Boolean, default=True)

    product_type = relationship("DimProductType", back_populates="products")
    risk_level = relationship("DimRiskLevel", back_populates="products")
    metrics = relationship("ProductMetrics", back_populates="product", cascade="all, delete-orphan")
    holdings = relationship("HoldingStatus", back_populates="product", uselist=False)
    investments = relationship("InvestmentLog", back_populates="product")


class InvestmentLog(Base):
    __tablename__ = "investment_log"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=date.today, nullable=False)
    product_id = Column(Integer, ForeignKey("product_master.id"), nullable=False)
    action_id = Column(Integer, ForeignKey("dim_action_type.id"), nullable=False)
    amount = Column(Float, nullable=False)
    channel_id = Column(Integer, ForeignKey("dim_account.id"))
    cashflow_link_id = Column(Integer, ForeignKey("cash_flow.id"))
    remark = Column(Text)

    product = relationship("ProductMaster", back_populates="investments")
    action = relationship("DimActionType", back_populates="investment_logs")
    channel = relationship("DimAccount", back_populates="investment_logs")
    cashflow_link = relationship("CashFlow", back_populates="investment")


class ProductMetrics(Base):
    __tablename__ = "product_metrics"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product_master.id"), nullable=False)
    record_date = Column(Date, nullable=False)
    metric_1 = Column(Float)
    metric_2 = Column(Float)
    metric_3 = Column(Float)
    source = Column(String)
    remark = Column(Text)

    product = relationship("ProductMaster", back_populates="metrics")


class HoldingStatus(Base):
    __tablename__ = "holding_status"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product_master.id"), nullable=False)
    total_invest = Column(Float, default=0)
    est_profit = Column(Float, default=0)
    avg_yield = Column(Float, default=0)
    last_update = Column(Date)

    product = relationship("ProductMaster", back_populates="holdings")


class OcrPending(Base):
    __tablename__ = "ocr_pending"

    id = Column(Integer, primary_key=True, index=True)
    module = Column(String, nullable=False)
    image_path = Column(String, nullable=False)
    status = Column(String, default="pending")
    extracted_data = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
