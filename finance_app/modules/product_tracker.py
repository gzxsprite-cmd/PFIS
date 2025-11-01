"""理财产品追踪模块，支持产品主档维护与时序指标记录。"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from . import master_data, ocr_pending


def get_active_products(conn) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT id, product_name
        FROM product_master
        WHERE is_active = 1
        ORDER BY product_name
        """,
        conn,
    )


def add_product(conn, name: str, type_id: Optional[int], risk_level_id: Optional[int], launch_date: Optional[date], remark: str) -> int:
    if not name:
        raise ValueError("产品名称不能为空")
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO product_master (product_name, type_id, risk_level_id, launch_date, remark)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, type_id, risk_level_id, str(launch_date) if launch_date else None, remark),
    )
    conn.commit()
    cur.execute("SELECT id FROM product_master WHERE product_name = ?", (name,))
    row = cur.fetchone()
    return row[0] if row else -1


def add_product_metric(
    conn,
    product_id: int,
    record_date: date,
    metric_1: Optional[float],
    metric_2: Optional[float],
    metric_3: Optional[float],
    source: Optional[str],
    remark: Optional[str],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO product_metrics
        (product_id, record_date, metric_1, metric_2, metric_3, source, remark)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_id,
            str(record_date),
            metric_1,
            metric_2,
            metric_3,
            source,
            remark,
        ),
    )
    conn.commit()


def get_product_trend(conn, product_id: int) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT record_date, metric_1, metric_2, metric_3, source
        FROM product_metrics
        WHERE product_id = ?
        ORDER BY record_date
        """,
        conn,
        params=(product_id,),
    )


def _render_product_table(conn) -> None:
    df = pd.read_sql(
        """
        SELECT pm.id, pm.product_name, t.name AS type, r.name AS risk_level, pm.launch_date, pm.remark, pm.is_active
        FROM product_master pm
        LEFT JOIN dim_product_type t ON pm.type_id = t.id
        LEFT JOIN dim_risk_level r ON pm.risk_level_id = r.id
        ORDER BY pm.product_name
        """,
        conn,
    )
    st.dataframe(df, use_container_width=True)


def _render_product_form(conn) -> None:
    st.markdown("#### 新增理财产品")
    with st.form("product_form"):
        name = st.text_input("产品名称")
        type_id = master_data.render_select_with_add(conn, "产品类型", "dim_product_type", "prod_type")
        risk_level_id = master_data.render_select_with_add(conn, "风险等级", "dim_risk_level", "prod_risk")
        use_launch_date = st.checkbox("填写发行日期", value=False, key="use_launch_date")
        launch_date_input = st.date_input(
            "发行日期",
            value=date.today(),
            key="launch_date",
            disabled=not use_launch_date,
        )
        launch_date = launch_date_input if use_launch_date else None
        remark = st.text_area("备注")
        submitted = st.form_submit_button("保存产品")
        if submitted:
            try:
                product_id = add_product(conn, name.strip(), type_id, risk_level_id, launch_date, remark)
                if product_id > 0:
                    st.success("产品已创建")
                    st.experimental_rerun()
                else:
                    st.info("产品已存在，将直接使用现有记录。")
                    st.experimental_rerun()
            except ValueError as exc:
                st.warning(str(exc))


def _render_metric_form(conn) -> None:
    st.markdown("#### 新增产品时序指标")
    products = get_active_products(conn)
    if products.empty:
        st.info("请先新增产品再记录指标。")
        return
    product_options = products.to_dict("records")
    name_to_id = {row["product_name"]: row["id"] for row in product_options}
    with st.form("metric_form"):
        product_name = st.selectbox("选择产品", list(name_to_id.keys()))
        record_date = st.date_input("记录日期", value=date.today())
        metric_1 = st.number_input("指标1 (近收益率%)", value=0.0, step=0.1)
        metric_2 = st.number_input("指标2", value=0.0, step=0.1)
        metric_3 = st.number_input("指标3", value=0.0, step=0.1)
        source = st.text_input("数据来源")
        remark = st.text_area("备注")
        submitted = st.form_submit_button("保存指标")
        if submitted:
            add_product_metric(
                conn,
                name_to_id[product_name],
                record_date,
                metric_1,
                metric_2,
                metric_3,
                source,
                remark,
            )
            st.success("指标已保存")
            st.experimental_rerun()


def _render_trend(conn) -> None:
    st.markdown("#### 产品收益曲线")
    products = get_active_products(conn)
    if products.empty:
        st.info("暂无产品可展示。")
        return
    product_options = products.to_dict("records")
    name_to_id = {row["product_name"]: row["id"] for row in product_options}
    selected_name = st.selectbox("选择产品查看曲线", list(name_to_id.keys()), key="trend_product")
    df = get_product_trend(conn, name_to_id[selected_name])
    if df.empty:
        st.info("该产品尚无时序数据。")
        return
    fig = px.line(df, x="record_date", y="metric_1", title=f"{selected_name} 指标1 趋势")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True)


def page(conn) -> None:
    st.subheader("📊 理财产品追踪")
    st.caption("维护产品主档，记录历史收益指标，并进行趋势分析。")

    _render_product_table(conn)

    col1, col2 = st.columns(2)
    with col1:
        _render_product_form(conn)
    with col2:
        _render_metric_form(conn)

    _render_trend(conn)

    st.markdown("### 📷 上传产品资料截图（OCR 预留）")
    uploaded = st.file_uploader("上传产品公告或说明", type=["png", "jpg", "jpeg"], key="prod_upload")
    if uploaded:
        path = ocr_pending.upload_image_for_ocr(conn, "products", uploaded)
        if path:
            st.info(f"截图已保存：{path}")
