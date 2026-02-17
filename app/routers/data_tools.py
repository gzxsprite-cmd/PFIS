from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime
from io import BytesIO
from typing import Any, Dict, Iterable

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from sqlalchemy import inspect, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    CashFlow,
    DimAccount,
    DimActionType,
    DimCategory,
    DimInvestmentTerm,
    DimMetric,
    DimProductType,
    DimRiskLevel,
    DimSourceType,
    HoldingStatus,
    InvestmentLog,
    OcrPending,
    ProductMaster,
    ProductMetric,
)
from ..utils import encode_header_value

router = APIRouter(prefix="/data", tags=["Data"], include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


MODEL_SHEET_MAP: OrderedDict[str, Any] = OrderedDict(
    [
        ("dim_account", DimAccount),
        ("dim_category", DimCategory),
        ("dim_source_type", DimSourceType),
        ("dim_action_type", DimActionType),
        ("dim_product_type", DimProductType),
        ("dim_risk_level", DimRiskLevel),
        ("dim_metric", DimMetric),
        ("dim_investment_term", DimInvestmentTerm),
        ("product_master", ProductMaster),
        ("holding_status", HoldingStatus),
        ("investment_log", InvestmentLog),
        ("cash_flow", CashFlow),
        ("product_metrics", ProductMetric),
        ("ocr_pending", OcrPending),
    ]
)


def _model_to_dict(instance: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for column in instance.__table__.columns:  # type: ignore[attr-defined]
        value = getattr(instance, column.name)
        if isinstance(value, datetime):
            payload[column.name] = value.replace(tzinfo=None)
        elif isinstance(value, date):
            payload[column.name] = value
        else:
            payload[column.name] = value
    return payload


def _coerce_value(column, value: Any) -> Any:  # type: ignore[no-untyped-def]
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if hasattr(pd, "isna") and pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()

    try:
        python_type = column.type.python_type  # type: ignore[attr-defined]
    except (AttributeError, NotImplementedError):
        return value

    if python_type is datetime:
        if isinstance(value, datetime):
            return value.replace(tzinfo=None)
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        return pd.to_datetime(value).to_pydatetime()

    if python_type is date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return pd.to_datetime(value).date()

    if python_type is int:
        if value == "":
            return None
        return int(value)

    if python_type is float:
        if value == "":
            return None
        return float(value)

    if python_type is bool:
        if isinstance(value, str):
            return value.lower() in {"true", "1", "yes"}
        return bool(value)

    return value


def _clean_record(model: Any, record: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for column in model.__table__.columns:  # type: ignore[attr-defined]
        column_name = column.name
        value = record.get(column_name)
        if value is None or (isinstance(value, float) and pd.isna(value)):
            cleaned[column_name] = None
        else:
            cleaned[column_name] = _coerce_value(column, value)
    return cleaned


def _dataframe_from_items(items: Iterable[Any], model: Any) -> pd.DataFrame:
    rows = [_model_to_dict(item) for item in items]
    if not rows:
        columns = [column.name for column in model.__table__.columns]  # type: ignore[attr-defined]
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows)


@router.get("/export", response_class=StreamingResponse)
def export_all_data(db: Session = Depends(get_db)) -> StreamingResponse:
    workbook = Workbook()
    default_sheet = workbook.active

    for sheet_name, model in MODEL_SHEET_MAP.items():
        queryset = db.query(model)
        pk_columns = inspect(model).primary_key
        if pk_columns:
            queryset = queryset.order_by(*pk_columns)
        worksheet = workbook.create_sheet(title=sheet_name)
        df = _dataframe_from_items(queryset.all(), model)
        if not df.empty:
            for row in dataframe_to_rows(df, index=False, header=True):
                worksheet.append(list(row))
        else:
            worksheet.append([column.name for column in model.__table__.columns])  # type: ignore[attr-defined]

    workbook.remove(default_sheet)
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    filename = f"PFIS_Backup_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
    }
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/import_form", response_class=HTMLResponse)
def import_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "partials/data_import_modal.html",
        {"request": request},
    )


@router.post("/import", response_class=HTMLResponse)
async def import_data(
    request: Request,
    file: UploadFile = File(...),
    mode: str = Form("replace"),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    if not file.filename.endswith(".xlsx"):
        return templates.TemplateResponse(
            "partials/data_import_result.html",
            {
                "request": request,
                "summary": {"错误": "仅支持 .xlsx 文件"},
                "status": "error",
            },
        )

    contents = await file.read()
    try:
        data_frames = pd.read_excel(BytesIO(contents), sheet_name=None)
    except Exception as exc:  # pragma: no cover - pandas/engine raises variety of errors
        return templates.TemplateResponse(
            "partials/data_import_result.html",
            {
                "request": request,
                "summary": {"导入失败": str(exc)},
                "status": "error",
            },
        )

    mode_normalized = (mode or "replace").lower()
    mode_normalized = mode_normalized if mode_normalized in {"replace", "append"} else "replace"

    summary: Dict[str, Any] = {}
    deferred_relationships: list[tuple[Any, str, Any, str, Any]] = []

    if mode_normalized == "replace":
        delete_order = [
            "product_metrics",
            "investment_log",
            "cash_flow",
            "holding_status",
            "product_master",
            "ocr_pending",
            "dim_metric",
            "dim_action_type",
            "dim_source_type",
            "dim_category",
            "dim_account",
            "dim_product_type",
            "dim_risk_level",
            "dim_investment_term",
        ]
        for sheet_name in delete_order:
            model = MODEL_SHEET_MAP.get(sheet_name)
            if not model:
                continue
            try:
                db.query(model).delete(synchronize_session=False)
            except Exception as exc:  # pragma: no cover - defensive guard
                db.rollback()
                summary[sheet_name] = f"清空失败：{exc}"
        db.commit()

    for sheet_name, model in MODEL_SHEET_MAP.items():
        df = data_frames.get(sheet_name)
        if df is None:
            summary[sheet_name] = "模板缺失"
            continue

        columns = [column.name for column in model.__table__.columns]  # type: ignore[attr-defined]
        missing_columns = [column for column in columns if column not in df.columns]
        if missing_columns:
            summary[sheet_name] = f"缺少列: {', '.join(missing_columns)}"
            continue

        records = df.replace({pd.NA: None}).to_dict(orient="records")
        processed = 0

        try:
            pk_columns = inspect(model).primary_key
            pk_name = pk_columns[0].name if pk_columns else "id"

            for record in records:
                cleaned = _clean_record(model, record)
                pk_value = cleaned.get(pk_name)

                link_column = None
                if sheet_name == "cash_flow":
                    link_column = "link_investment_id"
                elif sheet_name == "investment_log":
                    link_column = "cashflow_link_id"

                link_value = None
                if link_column:
                    link_value = cleaned.pop(link_column, None)

                if mode_normalized == "append" and not pk_value:
                    cleaned.pop(pk_name, None)

                if mode_normalized == "append" and pk_value:
                    instance = db.get(model, pk_value)
                    if instance:
                        for key, value in cleaned.items():
                            setattr(instance, key, value)
                    else:
                        instance = model(**cleaned)
                        db.add(instance)
                        db.flush()
                        pk_value = getattr(instance, pk_name)
                else:
                    instance = model(**cleaned)
                    db.add(instance)
                    db.flush()
                    pk_value = getattr(instance, pk_name)

                if link_column and link_value is not None:
                    deferred_relationships.append((model, pk_name, pk_value, link_column, link_value))

                processed += 1

            db.commit()
            summary[sheet_name] = f"导入成功：{processed} 条"
        except Exception as exc:  # pragma: no cover - safety net for Excel issues
            db.rollback()
            summary[sheet_name] = f"导入失败：{exc}"

    if deferred_relationships:
        try:
            for model, pk_name, identifier, column_name, value in deferred_relationships:
                if identifier is None or value is None:
                    continue
                db.execute(
                    update(model)
                    .where(getattr(model, pk_name) == identifier)
                    .values({column_name: value})
                )
            db.commit()
        except Exception as exc:  # pragma: no cover - defensive guard
            db.rollback()
            summary["关系同步"] = f"更新关联字段失败：{exc}"

    response = templates.TemplateResponse(
        "partials/data_import_result.html",
        {
            "request": request,
            "summary": summary,
            "status": "ok",
        },
    )
    response.headers["HX-Toast"] = encode_header_value("数据导入完成")
    return response

