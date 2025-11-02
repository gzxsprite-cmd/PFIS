from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def _column_exists(engine: Engine, table: str, column: str) -> bool:
    if engine.dialect.name != "sqlite":
        # For non-SQLite engines rely on SQLAlchemy metadata migrations elsewhere.
        return True

    pragma = text(f"PRAGMA table_info({table})")
    with engine.connect() as conn:
        result = conn.execute(pragma)
        for row in result:
            # SQLite PRAGMA table_info returns rows where index 1 is the column name
            if row[1] == column:
                return True
    return False


def run_migrations(engine: Engine) -> None:
    """Apply lightweight, SQLite-friendly migrations for existing installations."""

    if engine.dialect.name != "sqlite":
        return

    if not _column_exists(engine, "product_master", "investment_term_id"):
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE product_master ADD COLUMN investment_term_id INTEGER"))
