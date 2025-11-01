"""Streamlit 主入口。运行： streamlit run app.py"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from modules import analytics, cash_flow, investment_log, master_data, ocr_pending, product_tracker, simulation_lab

DB_PATH = Path("db/finance.db")


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def load_style() -> None:
    style_path = Path("static/style.css")
    if style_path.exists():
        with open(style_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def show_home(conn: sqlite3.Connection) -> None:
    st.markdown("### 欢迎使用个人理财与投资管理系统 v1.0")
    st.write(
        "本系统支持现金流记录、理财操作跟踪、主数据维护与模拟分析，所有数据仅存储于本地 SQLite 数据库。"
    )

    col1, col2 = st.columns(2)
    with col1:
        cash_df = pd.read_sql("SELECT COUNT(*) AS cnt FROM cash_flow", conn)
        st.metric("现金流记录数", int(cash_df.loc[0, "cnt"]))
    with col2:
        invest_df = pd.read_sql("SELECT COUNT(*) AS cnt FROM investment_log", conn)
        st.metric("理财操作记录数", int(invest_df.loc[0, "cnt"]))

    st.markdown("#### 快速开始")
    st.markdown(
        "1. 在左侧导航进入 **主数据维护**，完善账户、分类、产品类型等基础数据。\n"
        "2. 通过 **理财产品追踪** 新增产品与指标。\n"
        "3. 在 **理财操作** 与 **收支记录** 中录入每日流水，系统将自动联动校验。\n"
        "4. 使用 **模拟分析** 模块评估新的投资计划。"
    )


st.set_page_config(page_title="个人理财系统 v1.0", layout="wide")
load_style()

conn = get_conn()

nav = st.sidebar.radio(
    "导航",
    [
        "🏠 首页",
        "💰 收支记录",
        "📈 理财操作",
        "📊 理财产品追踪",
        "🧪 模拟分析",
        "📉 分析中心",
        "🧩 主数据维护",
        "⚙️ 系统设置",
    ],
)

if nav == "🏠 首页":
    show_home(conn)
elif nav == "💰 收支记录":
    cash_flow.page(conn)
elif nav == "📈 理财操作":
    investment_log.page(conn)
elif nav == "📊 理财产品追踪":
    product_tracker.page(conn)
elif nav == "🧪 模拟分析":
    simulation_lab.page(conn)
elif nav == "📉 分析中心":
    analytics.page(conn)
elif nav == "🧩 主数据维护":
    master_data.page(conn)
elif nav == "⚙️ 系统设置":
    st.subheader("系统设置")
    st.markdown(f"**数据库路径：** `{DB_PATH}`")
    if st.button("重新初始化数据库"):
        from db_init import create_tables

        create_tables()
        st.success("数据库结构已检查，可重新加载页面。")
    st.markdown("---")
    ocr_pending.view_pending(conn)

conn.close()
