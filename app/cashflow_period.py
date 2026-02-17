from __future__ import annotations

from datetime import date
from typing import Optional


def calculate_recent_month_range(range_months: int, today: Optional[date] = None) -> tuple[str, str]:
    if range_months <= 0:
        raise ValueError("range_months must be positive")
    today = today or date.today()
    end = date(today.year, today.month, 1)
    start_year = end.year
    start_month_value = end.month - range_months + 1
    while start_month_value <= 0:
        start_year -= 1
        start_month_value += 12
    start = date(start_year, start_month_value, 1)
    return start.strftime("%Y-%m"), end.strftime("%Y-%m")


def resolve_period(
    start_month: Optional[str],
    end_month: Optional[str],
    range_months: Optional[int],
    today: Optional[date] = None,
) -> tuple[Optional[str], Optional[str], Optional[int]]:
    if range_months in {3, 6, 12}:
        start_month, end_month = calculate_recent_month_range(range_months, today=today)
        return start_month, end_month, range_months

    if start_month and end_month:
        return start_month, end_month, None

    return start_month, end_month, None


def period_label(start_month: Optional[str], end_month: Optional[str]) -> str:
    if start_month and end_month:
        return f"{start_month} ~ {end_month}"
    return "全部时间"
