"""Add group fields to order_pi_records table.

Columns added:
  - group_id           INTEGER  (组内唯一标识，同一订单内子项指向组头)
  - group_name         TEXT     (组名称，用户编辑)
  - is_group_header    BOOLEAN  (是否为组头行)
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "shipping_helper.db")


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = [row[1] for row in cursor.fetchall()]
    return column_name in cols


def upgrade():
    """Add group_id, group_name, is_group_header to order_pi_records."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns_to_add = [
        ("group_id", "INTEGER"),
        ("group_name", "TEXT"),
        ("is_group_header", "INTEGER DEFAULT 0"),
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

    print(f"Migration 015: added {added}, skipped (already exist) {skipped}")


def downgrade():
    """SQLite does not support DROP COLUMN — manual rollback required."""
    raise NotImplementedError(
        "SQLite does not support DROP COLUMN. Manual rollback required."
    )


if __name__ == "__main__":
    upgrade()
