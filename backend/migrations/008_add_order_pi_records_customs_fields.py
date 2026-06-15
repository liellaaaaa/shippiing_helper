"""Add customs fields to order_pi_records table.

The Python model (OrderPiRecord) declares these 4 fields but migration 003
didn't include them in CREATE TABLE. This migration brings the DB schema
in sync with the model so save_service.save_record can write to them.

Columns added:
  - product_code           TEXT  (HS code 来自 customs_codes.json)
  - components             TEXT  (报关成分)
  - product_appearance     TEXT  (产品外观)
  - customs_match_status   TEXT  (报关匹配状态: matched/filled/conflict)
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "shipping_helper.db")


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = [row[1] for row in cursor.fetchall()]
    return column_name in cols


def upgrade():
    """Add 4 missing customs columns to order_pi_records."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns_to_add = [
        ("product_code", "TEXT"),
        ("components", "TEXT"),
        ("product_appearance", "TEXT"),
        ("customs_match_status", "TEXT"),
    ]

    added = []
    skipped = []
    for col_name, col_type in columns_to_add:
        if _column_exists(cursor, "order_pi_records", col_name):
            skipped.append(col_name)
        else:
            cursor.execute(
                f"ALTER TABLE order_pi_records ADD COLUMN {col_name} {col_type}"
            )
            added.append(col_name)

    conn.commit()
    conn.close()

    print(f"Migration 008: added {added}, skipped (already exist) {skipped}")


def downgrade():
    """SQLite 不支持 DROP COLUMN — 无法直接回滚，需要重建表。"""
    raise NotImplementedError(
        "SQLite does not support DROP COLUMN. Manual rollback required."
    )


if __name__ == "__main__":
    upgrade()
