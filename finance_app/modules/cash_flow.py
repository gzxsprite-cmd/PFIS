"""收支记录模块，实现流水录入与统计。"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from . import master_data, ocr_pending


def get_cash_flow(conn, start_date: Optional[date] = None, end_date: Optional[date] = None) -> pd.DataFrame:
    query = """
        SELECT c.id,
               c.date,
               a.name AS account,
               cat.name AS category,
               c.flow_type,
               c.amount,
               src.name AS source_type,
               c.remark,
               c.link_investment_id
        FROM cash_flow c
        LEFT JOIN dim_account a ON c.account_id = a.id
        LEFT JOIN dim_category cat ON c.category_id = cat.id
        LEFT JOIN dim_source_type src ON c.source_type_id = src.id
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND c.date >= ?"
        params.append(str(start_date))
    if end_date:
        query += " AND c.date <= ?"
        params.append(str(end_date))
    query += " ORDER BY c.date DESC, c.id DESC"
    return pd.read_sql(query, conn, params=params)


def add_cash_flow(
    conn,
    flow_date: date,
    account_id: int,
    category_id: Optional[int],
    flow_type: str,
    amount: float,
    source_type_id: Optional[int],
    remark: str,
    link_investment_id: Optional[int] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO cash_flow (date, account_id, category_id, flow_type, amount, source_type_id, remark, link_investment_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(flow_date),
            account_id,
            category_id,
            flow_type,
            amount,
            source_type_id,
            remark,
            link_investment_id,
        ),
    )
    conn.commit()


def summarize_cash_flow(conn) -> pd.DataFrame:
    query = """
        SELECT strftime('%Y-%m', date) AS month,
               SUM(CASE WHEN flow_type='收入' THEN amount ELSE 0 END) AS income,
               SUM(CASE WHEN flow_type='支出' THEN amount ELSE 0 END) AS expense,
               SUM(CASE WHEN flow_type='收入' THEN amount ELSE -amount END) AS balance
        FROM cash_flow
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month DESC
    """
    return pd.read_sql(query, conn)


def page(conn) -> None:
    st.subheader("💰 收支记录")
    st.caption("记录日常收支流水，并支持与理财操作联动校验。")

    with st.expander("筛选条件", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            enable_start = st.checkbox("启用开始日期", value=False, key="cf_start_enable")
            start_date_input = st.date_input(
                "开始日期",
                value=date.today(),
                key="cashflow_start",
                disabled=not enable_start,
            )
            start_date = start_date_input if enable_start else None
        with col2:
            enable_end = st.checkbox("启用结束日期", value=False, key="cf_end_enable")
            end_date_input = st.date_input(
                "结束日期",
                value=date.today(),
                key="cashflow_end",
                disabled=not enable_end,
            )
            end_date = end_date_input if enable_end else None

    df = get_cash_flow(conn, start_date, end_date)
    st.dataframe(df, use_container_width=True)

    if not df.empty:
        monthly_summary = summarize_cash_flow(conn)
        fig = px.bar(
            monthly_summary,
            x="month",
            y=["income", "expense"],
            barmode="group",
            title="月度收支对比",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("### 新增收支记录")

    with st.form("cashflow_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            flow_date = st.date_input("日期", value=date.today())
            flow_type = st.selectbox("类型", ["收入", "支出"])
        with col2:
            account_id = master_data.render_select_with_add(conn, "账户", "dim_account", "cf_account")
            category_id = master_data.render_select_with_add(conn, "分类", "dim_category", "cf_category", allow_none=True)
        with col3:
            source_type_id = master_data.render_select_with_add(conn, "来源", "dim_source_type", "cf_source", allow_none=True)
            amount = st.number_input("金额", min_value=0.0, step=100.0)
        remark = st.text_area("备注")
        submitted = st.form_submit_button("保存")

        if submitted:
            if account_id is None:
                st.warning("请选择账户或新增账户后再保存。")
            elif amount <= 0:
                st.warning("金额需大于0。")
            else:
                add_cash_flow(
                    conn,
                    flow_date,
                    account_id,
                    category_id,
                    flow_type,
                    amount,
                    source_type_id,
                    remark,
                )
                st.success("收支记录已保存。")
                st.experimental_rerun()

    st.markdown("### 📷 上传银行流水截图（OCR 预留）")
    uploaded = st.file_uploader("上传银行流水截图", type=["png", "jpg", "jpeg"])
    if uploaded:
        path = ocr_pending.upload_image_for_ocr(conn, "cashflow", uploaded)
        if path:
            st.info(f"截图已保存：{path}")
