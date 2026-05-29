"""Add pi_contracts, pi_contract_items, and pi_data tables."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "shipping_helper.db")


def upgrade():
    """Create pi_contracts, pi_contract_items, and pi_data tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create pi_contracts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pi_contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pi_no TEXT NOT NULL,
            customer_code TEXT,
            sales_person TEXT,
            pi_date TEXT,
            is_ordered TEXT DEFAULT '0',
            order_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)

    # Create pi_contract_items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pi_contract_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pi_contract_id INTEGER NOT NULL,
            internal_code TEXT NOT NULL,
            quantity REAL,
            unit_price REAL,
            total_amount REAL,
            product_color TEXT,
            hs_code TEXT,
            customs_name TEXT,
            customs_composition TEXT,
            order_customs_name TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pi_contract_id) REFERENCES pi_contracts(id) ON DELETE CASCADE
        )
    """)

    # Create pi_data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pi_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            internal_code TEXT UNIQUE NOT NULL,
            product_color TEXT,
            hs_code TEXT,
            customs_name TEXT,
            customs_composition TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("Migration 001: pi_contracts, pi_contract_items, pi_data tables created successfully")


def downgrade():
    """Drop all tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS pi_contract_items")
    cursor.execute("DROP TABLE IF EXISTS pi_contracts")
    cursor.execute("DROP TABLE IF EXISTS pi_data")

    conn.commit()
    conn.close()
    print("Migration 001: tables dropped")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()