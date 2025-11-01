"""
初始化 finance.db
执行方式： python db_init.py
"""

import os
import sqlite3

DB_PATH = os.path.join("db", "finance.db")


def create_tables():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ---------------- 主数据表 ----------------
    cur.executescript(
        """
    CREATE TABLE IF NOT EXISTS dim_account(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        status TEXT DEFAULT 'active',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_used DATETIME
    );

    CREATE TABLE IF NOT EXISTS dim_category(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        parent_id INTEGER,
        status TEXT DEFAULT 'active',
        FOREIGN KEY(parent_id) REFERENCES dim_category(id)
    );

    CREATE TABLE IF NOT EXISTS dim_product_type(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        status TEXT DEFAULT 'active'
    );

    CREATE TABLE IF NOT EXISTS dim_risk_level(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS dim_action_type(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dim_source_type(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
        """
    )

    # ---------------- 主业务表 ----------------
    cur.executescript(
        """
    CREATE TABLE IF NOT EXISTS cash_flow(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        account_id INTEGER NOT NULL,
        category_id INTEGER,
        flow_type TEXT CHECK(flow_type IN ('收入','支出')),
        amount REAL NOT NULL,
        source_type_id INTEGER,
        remark TEXT,
        link_investment_id INTEGER,
        FOREIGN KEY(account_id) REFERENCES dim_account(id),
        FOREIGN KEY(category_id) REFERENCES dim_category(id),
        FOREIGN KEY(source_type_id) REFERENCES dim_source_type(id)
    );

    CREATE TABLE IF NOT EXISTS product_master(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT UNIQUE NOT NULL,
        type_id INTEGER,
        risk_level_id INTEGER,
        launch_date DATE,
        remark TEXT,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY(type_id) REFERENCES dim_product_type(id),
        FOREIGN KEY(risk_level_id) REFERENCES dim_risk_level(id)
    );

    CREATE TABLE IF NOT EXISTS investment_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        product_id INTEGER NOT NULL,
        action_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        channel_id INTEGER,
        cashflow_link_id INTEGER,
        remark TEXT,
        FOREIGN KEY(product_id) REFERENCES product_master(id),
        FOREIGN KEY(action_id) REFERENCES dim_action_type(id),
        FOREIGN KEY(channel_id) REFERENCES dim_account(id),
        FOREIGN KEY(cashflow_link_id) REFERENCES cash_flow(id)
    );

    CREATE TABLE IF NOT EXISTS product_metrics(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        record_date DATE NOT NULL,
        metric_1 REAL,
        metric_2 REAL,
        metric_3 REAL,
        source TEXT,
        remark TEXT,
        FOREIGN KEY(product_id) REFERENCES product_master(id),
        UNIQUE(product_id, record_date)
    );

    CREATE TABLE IF NOT EXISTS holding_status(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        total_invest REAL DEFAULT 0,
        est_profit REAL DEFAULT 0,
        avg_yield REAL DEFAULT 0,
        last_update DATE,
        FOREIGN KEY(product_id) REFERENCES product_master(id)
    );

    CREATE TABLE IF NOT EXISTS ocr_pending(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module TEXT NOT NULL,
        image_path TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        extracted_data TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
        """
    )

    conn.commit()

    seed_master_data(conn)

    conn.close()
    print("✅ finance.db 初始化完成")


def seed_master_data(conn: sqlite3.Connection) -> None:
    """初始化常用主数据，方便首次使用。"""
    master_defaults = {
        "dim_account": ["现金账户", "银行卡", "证券账户"],
        "dim_category": ["工资收入", "生活支出", "投资转出", "投资回流"],
        "dim_product_type": ["货币基金", "股票基金", "债券"],
        "dim_risk_level": ["低", "中", "高"],
        "dim_action_type": ["买入", "赎回", "分红"],
        "dim_source_type": ["工资", "理财", "其他"]
    }

    cur = conn.cursor()
    for table, names in master_defaults.items():
        for name in names:
            if table == "dim_risk_level":
                cur.execute(
                    "INSERT OR IGNORE INTO dim_risk_level (name, description) VALUES (?, ?)",
                    (name, f"默认{name}风险等级"),
                )
            elif table == "dim_category":
                cur.execute(
                    "INSERT OR IGNORE INTO dim_category (name) VALUES (?)",
                    (name,),
                )
            else:
                cur.execute(
                    f"INSERT OR IGNORE INTO {table} (name) VALUES (?)",
                    (name,),
                )
    conn.commit()


if __name__ == "__main__":
    create_tables()
