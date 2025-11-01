"""模拟分析模块，提供买入前的收益风险评估。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional

import numpy as np
import pandas as pd
import streamlit as st

from . import investment_log, master_data, product_tracker


@dataclass
class SimulationResult:
    product_id: int
    amount: float
    expected_profit: float
    expected_yield: float
    risk_level: str
    new_structure: pd.DataFrame


def _get_current_portfolio(conn) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT hs.product_id,
               pm.product_name,
               hs.total_invest
        FROM holding_status hs
        JOIN product_master pm ON hs.product_id = pm.id
        """,
        conn,
    )


def _get_risk_level(conn, product_id: int) -> str:
    cur = conn.execute(
        """
        SELECT rl.name
        FROM product_master pm
        LEFT JOIN dim_risk_level rl ON pm.risk_level_id = rl.id
        WHERE pm.id = ?
        """,
        (product_id,),
    )
    row = cur.fetchone()
    return row[0] if row and row[0] else "未评级"


def simulate_investment_change(conn, product_id: int, amount: float) -> Optional[SimulationResult]:
    metrics = product_tracker.get_product_trend(conn, product_id)
    if metrics.empty:
        expected_yield = 0.0
    else:
        recent = metrics.tail(min(30, len(metrics)))
        expected_yield = float(np.nanmean(recent["metric_1"])) / 100
    expected_profit = amount * expected_yield / 12 if amount else 0.0
    risk_level = _get_risk_level(conn, product_id)

    product_name_row = conn.execute(
        "SELECT product_name FROM product_master WHERE id = ?",
        (product_id,),
    ).fetchone()
    product_name = product_name_row[0] if product_name_row else "模拟产品"

    portfolio = _get_current_portfolio(conn)
    if portfolio.empty:
        new_structure = pd.DataFrame(
            {
                "product_id": [product_id],
                "product_name": [product_name],
                "amount": [amount],
                "ratio": [1.0 if amount else 0.0],
            }
        )
    else:
        if product_id in portfolio["product_id"].values:
            portfolio.loc[portfolio["product_id"] == product_id, "total_invest"] += amount
        else:
            portfolio = pd.concat(
                [
                    portfolio,
                    pd.DataFrame(
                        {
                            "product_id": [product_id],
                            "product_name": [product_name],
                            "total_invest": [amount],
                        }
                    ),
                ],
                ignore_index=True,
            )
        total = portfolio["total_invest"].sum()
        if total == 0:
            portfolio["ratio"] = 0
        else:
            portfolio["ratio"] = portfolio["total_invest"] / total
        portfolio.rename(columns={"total_invest": "amount"}, inplace=True)
        new_structure = portfolio[["product_id", "product_name", "amount", "ratio"]]

    return SimulationResult(
        product_id=product_id,
        amount=amount,
        expected_profit=expected_profit,
        expected_yield=expected_yield,
        risk_level=risk_level,
        new_structure=new_structure,
    )


def _ensure_buy_action(conn) -> int:
    cur = conn.execute("SELECT id FROM dim_action_type WHERE name = '买入'")
    row = cur.fetchone()
    if row:
        return row[0]
    return master_data.add_to_master(conn, "dim_action_type", "买入")


def page(conn) -> None:
    st.subheader("🧪 模拟分析")
    st.caption("在正式买入前评估收益与风险，确认后可直接生成买入记录。")

    portfolio = _get_current_portfolio(conn)
    if portfolio.empty:
        st.info("当前暂无持仓，首次买入后将在此展示。")
    else:
        total = portfolio["total_invest"].sum()
        portfolio["持仓占比"] = portfolio["total_invest"] / total
        st.dataframe(portfolio, use_container_width=True)

    products = product_tracker.get_active_products(conn)
    if products.empty:
        st.warning("请先维护理财产品。")
        return
    product_map: Dict[str, int] = {row["product_name"]: row["id"] for _, row in products.iterrows()}

    with st.form("simulate_form"):
        product_name = st.selectbox("拟买入产品", list(product_map.keys()))
        amount = st.number_input("拟买入金额", min_value=0.0, step=100.0)
        channel_id = master_data.render_select_with_add(conn, "资金渠道", "dim_account", "sim_channel")
        auto_cashflow = st.checkbox("同步生成现金流", value=True)
        submitted = st.form_submit_button("执行模拟")
        if submitted:
            if amount <= 0:
                st.warning("金额需大于0。")
            else:
                result = simulate_investment_change(conn, product_map[product_name], amount)
                st.session_state["simulation_result"] = {
                    "result": result,
                    "product_name": product_name,
                    "channel_id": channel_id,
                    "auto_cashflow": auto_cashflow,
                }
                st.success("模拟完成，请在下方查看结果。")

    sim_state = st.session_state.get("simulation_result")
    if sim_state:
        result: SimulationResult = sim_state["result"]
        if result is None:
            st.warning("缺少该产品的收益指标，无法计算预期收益。")
        else:
            st.markdown("### 模拟结果")
            st.metric("预期年化收益", f"{result.expected_yield * 100:.2f}%")
            st.metric("预计月度收益", f"{result.expected_profit:.2f}")
            st.info(f"风险等级：{result.risk_level}")
            st.dataframe(result.new_structure, use_container_width=True)
            if st.button("确认生成买入记录"):
                action_id = _ensure_buy_action(conn)
                investment_log.add_investment_log(
                    conn,
                    date.today(),
                    result.product_id,
                    action_id,
                    result.amount,
                    sim_state.get("channel_id"),
                    "模拟确认买入",
                    link_cashflow=sim_state.get("auto_cashflow", True),
                )
                st.success("已生成买入记录，持仓将自动更新。")
                del st.session_state["simulation_result"]
                st.experimental_rerun()
