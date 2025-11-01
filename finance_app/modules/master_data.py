"""主数据维护模块，提供统一的主数据增删查入口。"""

from __future__ import annotations

from typing import Dict, Iterable, Optional

import pandas as pd
import streamlit as st

TABLE_CONFIG: Dict[str, Dict[str, str]] = {
    "账户与渠道": {"table": "dim_account", "label": "name"},
    "收支类别": {"table": "dim_category", "label": "name"},
    "理财类型": {"table": "dim_product_type", "label": "name"},
    "风险等级": {"table": "dim_risk_level", "label": "name"},
    "操作类型": {"table": "dim_action_type", "label": "name"},
    "资金来源": {"table": "dim_source_type", "label": "name"},
}


STATUS_COLUMN_TABLES: Iterable[str] = {"dim_account", "dim_category", "dim_product_type"}


def get_options(conn, table_name: str) -> pd.DataFrame:
    """获取指定主数据表的选项。"""
    status_clause = ""
    if table_name in STATUS_COLUMN_TABLES:
        status_clause = "WHERE COALESCE(status, 'active') = 'active'"
    query = f"SELECT id, name FROM {table_name} {status_clause} ORDER BY name"
    return pd.read_sql(query, conn)


def add_to_master(conn, table_name: str, new_name: str, description: Optional[str] = None) -> int:
    """向主数据表新增一条记录，返回记录 ID。"""
    if not new_name:
        raise ValueError("名称不能为空")
    cur = conn.cursor()
    if table_name == "dim_risk_level":
        cur.execute(
            "INSERT OR IGNORE INTO dim_risk_level (name, description) VALUES (?, ?)",
            (new_name, description or "用户新增风险等级"),
        )
    else:
        cur.execute(
            f"INSERT OR IGNORE INTO {table_name} (name) VALUES (?)",
            (new_name,),
        )
    conn.commit()
    cur.execute(f"SELECT id FROM {table_name} WHERE name = ?", (new_name,))
    row = cur.fetchone()
    return row[0] if row else -1


def render_select_with_add(
    conn,
    label: str,
    table_name: str,
    key_prefix: str,
    help_text: Optional[str] = None,
    allow_none: bool = False,
) -> Optional[int]:
    """渲染带有“＋新增”功能的下拉框，返回选择的 ID。"""
    options_df = get_options(conn, table_name)
    options = options_df.to_dict("records")
    labels = [opt["name"] for opt in options]
    option_map = {opt["name"]: opt["id"] for opt in options}

    if allow_none:
        labels = ["(空)"] + labels

    labels.append("＋ 新增")

    selection = st.selectbox(label, labels, key=f"{key_prefix}_select", help=help_text)

    if selection == "＋ 新增":
        new_name = st.text_input(f"新增{label}", key=f"{key_prefix}_new")
        extra_desc = None
        if table_name == "dim_risk_level":
            extra_desc = st.text_area("风险等级说明", key=f"{key_prefix}_desc")
        if st.button(f"保存{label}", key=f"{key_prefix}_save"):
            try:
                add_to_master(conn, table_name, new_name.strip(), extra_desc)
                st.success(f"已新增 {new_name}")
                st.experimental_rerun()
            except ValueError as exc:
                st.warning(str(exc))
        return None
    if allow_none and selection == "(空)":
        return None
    return option_map.get(selection)


def _render_table(conn, title: str, table_name: str) -> None:
    st.markdown(f"### {title}")
    df = pd.read_sql(f"SELECT * FROM {table_name} ORDER BY id DESC", conn)
    st.dataframe(df, use_container_width=True)

    with st.form(f"form_{table_name}"):
        name = st.text_input("名称")
        extra_desc = None
        if table_name == "dim_risk_level":
            extra_desc = st.text_area("说明")
        submit = st.form_submit_button("新增")
        if submit:
            try:
                add_to_master(conn, table_name, name.strip(), extra_desc)
                st.success("新增成功")
                st.experimental_rerun()
            except ValueError as exc:
                st.warning(str(exc))


def page(conn) -> None:
    st.subheader("🧩 主数据维护")
    st.info("集中维护账户、分类、产品类型、风险等级等标准项，可供业务模块引用。")

    tab_titles = list(TABLE_CONFIG.keys())
    tabs = st.tabs(tab_titles)

    for tab, title in zip(tabs, tab_titles):
        with tab:
            config = TABLE_CONFIG[title]
            _render_table(conn, title, config["table"])
