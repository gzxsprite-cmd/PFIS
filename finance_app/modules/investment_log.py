"""理财操作记录模块，管理投资流水并与现金流联动。"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from . import cash_flow, master_data, ocr_pending, product_tracker

BUY_KEYWORDS = ("买", "申购", "加仓")
INCOME_KEYWORDS = ("赎", "分红", "回款", "派息", "卖")


def _get_action_name(conn, action_id: int) -> str:
    cur = conn.execute("SELECT name FROM dim_action_type WHERE id = ?", (action_id,))
    row = cur.fetchone()
    return row[0] if row else ""


def _match_flow_type(action_name: str) -> Optional[str]:
    if any(keyword in action_name for keyword in BUY_KEYWORDS):
        return "支出"
    if any(keyword in action_name for keyword in INCOME_KEYWORDS):
        return "收入"
    return None


def _get_category_id(conn, name: str) -> Optional[int]:
    cur = conn.execute("SELECT id FROM dim_category WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    return master_data.add_to_master(conn, "dim_category", name)


def _get_source_id(conn, name: str) -> Optional[int]:
    cur = conn.execute("SELECT id FROM dim_source_type WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    return master_data.add_to_master(conn, "dim_source_type", name)


def add_investment_log(
    conn,
    log_date: date,
    product_id: int,
    action_id: int,
    amount: float,
    channel_id: Optional[int],
    remark: str,
    link_cashflow: bool = True,
) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO investment_log (date, product_id, action_id, amount, channel_id, remark)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(log_date),
            product_id,
            action_id,
            amount,
            channel_id,
            remark,
        ),
    )
    log_id = cur.lastrowid
    conn.commit()

    if link_cashflow:
        action_name = _get_action_name(conn, action_id)
        flow_type = _match_flow_type(action_name)
        if flow_type:
            category_name = "投资转出" if flow_type == "支出" else "投资回流"
            category_id = _get_category_id(conn, category_name)
            source_id = _get_source_id(conn, "理财")
            cash_flow.add_cash_flow(
                conn,
                log_date,
                channel_id or _get_default_account(conn),
                category_id,
                flow_type,
                amount,
                source_id,
                f"理财操作：{action_name}",
                log_id,
            )
            cur.execute(
                "SELECT MAX(id) FROM cash_flow WHERE link_investment_id = ?",
                (log_id,),
            )
            cash_id = cur.fetchone()[0]
            if cash_id:
                conn.execute(
                    "UPDATE investment_log SET cashflow_link_id = ? WHERE id = ?",
                    (cash_id, log_id),
                )
                conn.commit()
    update_holdings(conn)
    return log_id


def _get_default_account(conn) -> int:
    cur = conn.execute("SELECT id FROM dim_account ORDER BY id LIMIT 1")
    row = cur.fetchone()
    if row:
        return row[0]
    return master_data.add_to_master(conn, "dim_account", "默认账户")


def get_investment_logs(conn) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT l.id,
               l.date,
               pm.product_name,
               act.name AS action,
               l.amount,
               acc.name AS channel,
               l.cashflow_link_id,
               l.remark
        FROM investment_log l
        LEFT JOIN product_master pm ON l.product_id = pm.id
        LEFT JOIN dim_action_type act ON l.action_id = act.id
        LEFT JOIN dim_account acc ON l.channel_id = acc.id
        ORDER BY l.date DESC, l.id DESC
        """,
        conn,
    )


def update_holdings(conn) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO holding_status (product_id, total_invest, est_profit, avg_yield, last_update)
        SELECT l.product_id,
               SUM(CASE WHEN instr(a.name, '买') > 0 OR instr(a.name, '申') > 0 THEN l.amount ELSE -l.amount END) AS total_invest,
               SUM(CASE WHEN instr(a.name, '赎') > 0 OR instr(a.name, '分红') > 0 OR instr(a.name, '回款') > 0 THEN l.amount ELSE 0 END)
               - SUM(CASE WHEN instr(a.name, '买') > 0 OR instr(a.name, '申') > 0 THEN l.amount ELSE 0 END) AS est_profit,
               0,
               DATE('now')
        FROM investment_log l
        JOIN dim_action_type a ON l.action_id = a.id
        GROUP BY l.product_id
        """
    )
    conn.commit()


def _calculate_monthly_consistency(conn) -> pd.DataFrame:
    invest = pd.read_sql(
        """
        SELECT strftime('%Y-%m', l.date) AS month,
               SUM(CASE WHEN instr(a.name, '买') > 0 OR instr(a.name, '申') > 0 THEN l.amount ELSE 0 END) AS invest_out,
               SUM(CASE WHEN instr(a.name, '赎') > 0 OR instr(a.name, '分红') > 0 OR instr(a.name, '回款') > 0 THEN l.amount ELSE 0 END) AS invest_in
        FROM investment_log l
        JOIN dim_action_type a ON l.action_id = a.id
        GROUP BY strftime('%Y-%m', l.date)
        """,
        conn,
    )
    cash = pd.read_sql(
        """
        SELECT strftime('%Y-%m', date) AS month,
               SUM(CASE WHEN flow_type='支出' THEN amount ELSE 0 END) AS cash_out,
               SUM(CASE WHEN flow_type='收入' THEN amount ELSE 0 END) AS cash_in
        FROM cash_flow
        WHERE link_investment_id IS NOT NULL
        GROUP BY strftime('%Y-%m', date)
        """,
        conn,
    )
    df = pd.merge(invest, cash, on="month", how="outer").fillna(0)
    df["支出差异"] = df["invest_out"] - df["cash_out"]
    df["收入差异"] = df["invest_in"] - df["cash_in"]
    return df.sort_values("month", ascending=False)


def page(conn) -> None:
    st.subheader("📈 理财操作记录")
    st.caption("记录理财买入、赎回、分红等操作，并自动与现金流联动。")

    df = get_investment_logs(conn)
    st.dataframe(df, use_container_width=True)

    if not df.empty:
        by_product = (
            df.groupby("product_name")["amount"].sum().reset_index().rename(columns={"amount": "累计金额"})
        )
        fig = px.bar(by_product, x="product_name", y="累计金额", title="产品累计操作金额")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("### 新增理财操作")

    products = product_tracker.get_active_products(conn)
    if products.empty:
        st.info("请先新增理财产品。可通过下方快速新增。")
    product_map = {row["product_name"]: row["id"] for _, row in products.iterrows()} if not products.empty else {}

    with st.form("investment_form"):
        log_date = st.date_input("操作日期", value=date.today())
        product_name = st.selectbox("理财产品", list(product_map.keys())) if product_map else None
        action_id = master_data.render_select_with_add(conn, "操作类型", "dim_action_type", "invest_action")
        channel_id = master_data.render_select_with_add(conn, "资金渠道", "dim_account", "invest_channel")
        amount = st.number_input("金额", min_value=0.0, step=100.0)
        remark = st.text_area("备注")
        auto_cashflow = st.checkbox("自动生成对应现金流", value=True)
        submitted = st.form_submit_button("保存理财操作")
        if submitted:
            if not product_name:
                st.warning("请先在下方新增理财产品后再保存。")
            elif action_id is None:
                st.warning("请先维护操作类型。")
            elif amount <= 0:
                st.warning("金额需大于0。")
            else:
                log_id = add_investment_log(
                    conn,
                    log_date,
                    product_map[product_name],
                    action_id,
                    amount,
                    channel_id,
                    remark,
                    link_cashflow=auto_cashflow,
                )
                st.success(f"记录已保存 (ID: {log_id})")
                st.experimental_rerun()

    with st.expander("⚡ 快速新增理财产品"):
        with st.form("quick_product_form"):
            name = st.text_input("产品名称", key="quick_prod_name")
            type_id = master_data.render_select_with_add(conn, "产品类型", "dim_product_type", "quick_prod_type")
            risk_id = master_data.render_select_with_add(conn, "风险等级", "dim_risk_level", "quick_prod_risk")
            remark = st.text_area("备注", key="quick_prod_remark")
            submitted = st.form_submit_button("新增产品")
            if submitted:
                try:
                    product_tracker.add_product(conn, name.strip(), type_id, risk_id, None, remark)
                    st.success("产品已新增，可在上方选择。")
                    st.experimental_rerun()
                except ValueError as exc:
                    st.warning(str(exc))

    st.markdown("### 📉 每月收支联动校验")
    consistency = _calculate_monthly_consistency(conn)
    st.dataframe(consistency, use_container_width=True)
    inconsistent = consistency[(consistency["支出差异"].abs() > 0.01) | (consistency["收入差异"].abs() > 0.01)]
    if not inconsistent.empty:
        st.warning("存在理财操作与现金流不平衡的月份，请核对差异。")
    else:
        st.success("所有月份的理财操作与现金流保持一致。")

    st.markdown("### 📷 上传理财凭证（OCR 预留）")
    uploaded = st.file_uploader("上传理财操作截图", type=["png", "jpg", "jpeg"], key="invest_upload")
    if uploaded:
        path = ocr_pending.upload_image_for_ocr(conn, "investment", uploaded)
        if path:
            st.info(f"截图已保存：{path}")
