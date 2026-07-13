"""Add currency column to order_pi_records table.

Columns added:
  - currency  TEXT  (币制：USD / CNY / RMB)
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "shipping_helper.db")


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = [row[1] for row in cursor.fetchall()]
    return column_name in cols


def upgrade():
    """Add currency column to order_pi_records."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if _column_exists(cursor, "order_pi_records", "currency"):
        print("Migration 014: column 'currency' already exists, skipped")
    else:
        cursor.execute("ALTER TABLE order_pi_records ADD COLUMN currency TEXT")
        print("Migration 014: added currency column")

    conn.commit()
    conn.close()


def downgrade():
    raise NotImplementedError("SQLite does not support DROP COLUMN.")


if __name__ == "__main__":
    upgrade()
