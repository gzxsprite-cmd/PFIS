from __future__ import annotations

from datetime import date
import unittest

from app.cashflow_period import calculate_recent_month_range, resolve_period


class CashflowRangeTests(unittest.TestCase):
    def test_recent_ranges(self):
        fake_today = date(2026, 1, 20)
        self.assertEqual(calculate_recent_month_range(3, fake_today), ("2025-11", "2026-01"))
        self.assertEqual(calculate_recent_month_range(6, fake_today), ("2025-08", "2026-01"))
        self.assertEqual(calculate_recent_month_range(12, fake_today), ("2025-02", "2026-01"))

    def test_resolve_period_uses_same_start_end_for_all_requests(self):
        start_month, end_month, mode = resolve_period(None, None, 6, today=date(2026, 1, 20))
        list_params = {"start_month": start_month, "end_month": end_month}
        ai_params = {"start_month": start_month, "end_month": end_month}
        self.assertEqual(mode, 6)
        self.assertEqual(list_params, ai_params)

    def test_manual_range_switches_to_custom(self):
        start_month, end_month, mode = resolve_period("2025-10", "2025-12", None)
        self.assertEqual((start_month, end_month, mode), ("2025-10", "2025-12", None))


if __name__ == "__main__":
    unittest.main()
