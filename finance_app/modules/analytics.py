"""分析中心模块，汇总现金流与持仓表现。"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from . import cash_flow, investment_log


def _portfolio_structure(conn) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT pm.product_name,
               hs.total_invest,
               hs.est_profit,
               hs.avg_yield
        FROM holding_status hs
        JOIN product_master pm ON hs.product_id = pm.id
        """,
        conn,
    )


def page(conn) -> None:
    st.subheader("📉 分析中心")
    st.caption("从现金流与持仓角度进行综合分析，并支持导出数据。")

    cash_summary = cash_flow.summarize_cash_flow(conn)
    holdings = _portfolio_structure(conn)
    logs = investment_log.get_investment_logs(conn)

    col1, col2, col3 = st.columns(3)
    total_income = cash_summary["income"].sum() if not cash_summary.empty else 0
    total_expense = cash_summary["expense"].sum() if not cash_summary.empty else 0
    balance = total_income - total_expense
    col1.metric("累计收入", f"{total_income:.2f}")
    col2.metric("累计支出", f"{total_expense:.2f}")
    col3.metric("累计结余", f"{balance:.2f}")

    if not cash_summary.empty:
        fig = px.line(cash_summary, x="month", y="balance", title="月度结余走势")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(cash_summary, use_container_width=True)
    else:
        st.info("暂无现金流数据。")

    st.markdown("---")
    st.markdown("### 持仓结构与收益")
    if holdings.empty:
        st.info("尚未生成持仓数据，可在录入理财操作后使用。")
    else:
        holdings["持仓占比"] = holdings["total_invest"] / holdings["total_invest"].sum()
        pie = px.pie(holdings, names="product_name", values="total_invest", title="持仓占比")
        st.plotly_chart(pie, use_container_width=True)
        st.dataframe(holdings, use_container_width=True)

    st.markdown("---")
    st.markdown("### 理财操作时间轴")
    if logs.empty:
        st.info("暂无理财操作记录。")
    else:
        timeline = logs.sort_values("date")
        fig = px.scatter(
            timeline,
            x="date",
            y="amount",
            color="action",
            hover_data=["product_name", "channel"],
            title="理财操作分布",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(timeline, use_container_width=True)

    st.markdown("---")
    st.markdown("### 数据导出")
    export_choice = st.selectbox(
        "选择导出数据表",
        ["cash_flow", "investment_log", "holding_status", "product_metrics"],
    )
    df = pd.read_sql(f"SELECT * FROM {export_choice}", conn)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    st.download_button(
        label="下载CSV",
        data=buffer.getvalue(),
        file_name=f"{export_choice}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
