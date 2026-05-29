"""Add order_pi_records table — Phase 1 unified workflow target table."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "shipping_helper.db")


def upgrade():
    """Create order_pi_records table (15-field wide table with packaging result)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_pi_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT,
            customer_code TEXT,
            customer_name TEXT,
            pi_no TEXT,
            sales_person TEXT,
            order_date TEXT,
            pi_date TEXT,
            delivery_date TEXT,
            internal_code TEXT,
            product_cn TEXT,
            product_en TEXT,
            spec_kg REAL,
            hs_code TEXT,
            customs_name TEXT,
            quantity_kg REAL,
            unit_price REAL,
            total_amount REAL,
            order_requirement TEXT,
            notes TEXT,
            packaging_type_id INTEGER,
            pallet_spec TEXT,
            drums_per_pallet INTEGER,
            drum_count INTEGER,
            pallet_count INTEGER,
            net_weight_kg REAL,
            gross_weight_kg REAL,
            volume_cbm REAL,
            fits_20gp TEXT,
            packaging_result_json TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (packaging_type_id) REFERENCES packaging_types(id)
        )
    """)

    conn.commit()
    conn.close()
    print("Migration 003: order_pi_records table created successfully")


def downgrade():
    """Drop order_pi_records table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS order_pi_records")

    conn.commit()
    conn.close()
    print("Migration 003: order_pi_records table dropped")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()