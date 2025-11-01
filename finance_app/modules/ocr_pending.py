"""OCR 预留模块，负责截图保存与待识别记录维护。"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

PENDING_ROOT = Path("pending_ocr")


MODULE_DIR_MAP = {
    "cashflow": PENDING_ROOT / "cashflow",
    "investment": PENDING_ROOT / "investment",
    "products": PENDING_ROOT / "products",
}


def ensure_directories() -> None:
    for path in MODULE_DIR_MAP.values():
        path.mkdir(parents=True, exist_ok=True)


def upload_image_for_ocr(conn, module: str, uploaded_file) -> Optional[str]:
    """保存上传的截图并在 ocr_pending 表记录。"""
    if not uploaded_file:
        return None

    ensure_directories()
    module_dir = MODULE_DIR_MAP.get(module, PENDING_ROOT)
    module_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uploaded_file.name}"
    file_path = module_dir / filename

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    conn.execute(
        "INSERT INTO ocr_pending (module, image_path) VALUES (?, ?)",
        (module, str(file_path)),
    )
    conn.commit()
    return str(file_path)


def view_pending(conn) -> None:
    st.subheader("OCR 上传记录")
    df = pd.read_sql("SELECT * FROM ocr_pending ORDER BY created_at DESC", conn)
    st.dataframe(df, use_container_width=True)
    st.caption("当前版本仅保存截图，后续版本将提供自动识别。")
