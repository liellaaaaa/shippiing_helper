"""
Migration 016: Add payment_terms and payment_method columns to pi_contracts table.

Columns added:
  - payment_terms   TEXT    付款条款原文 (e.g. "TT, 100% payment against BL copy")
  - payment_method  TEXT    付款方式分类: "TT" 电汇 / "LC" 信用证
"""

from sqlalchemy import text
from app.database import engine


def upgrade():
    with engine.connect() as conn:
        existing = conn.execute(text("PRAGMA table_info(pi_contracts)")).fetchall()
        col_names = [row[1] for row in existing]

        if "payment_terms" not in col_names:
            conn.execute(text("ALTER TABLE pi_contracts ADD COLUMN payment_terms TEXT"))
        if "payment_method" not in col_names:
            conn.execute(text("ALTER TABLE pi_contracts ADD COLUMN payment_method TEXT"))

        conn.commit()
    print("[016] Done: pi_contracts added payment_terms / payment_method columns")


def downgrade():
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE pi_contracts DROP COLUMN IF EXISTS payment_terms"))
        conn.execute(text("ALTER TABLE pi_contracts DROP COLUMN IF EXISTS payment_method"))
        conn.commit()
    print("[016] Downgrade: SQLite does not support real DROP COLUMN")


if __name__ == "__main__":
    upgrade()
