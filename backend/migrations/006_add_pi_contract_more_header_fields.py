"""
迁移 006: 给 pi_contracts 表新增 loading_port / price_term / invoice_to 字段
"""

from sqlalchemy import text
from app.database import engine


def upgrade():
    with engine.connect() as conn:
        # 检查列是否已存在（幂等）
        existing = conn.execute(text("PRAGMA table_info(pi_contracts)")).fetchall()
        col_names = [row[1] for row in existing]

        if "loading_port" not in col_names:
            conn.execute(text("ALTER TABLE pi_contracts ADD COLUMN loading_port TEXT"))
        if "price_term" not in col_names:
            conn.execute(text("ALTER TABLE pi_contracts ADD COLUMN price_term TEXT"))
        if "invoice_to" not in col_names:
            conn.execute(text("ALTER TABLE pi_contracts ADD COLUMN invoice_to TEXT"))

        conn.commit()
    print("[006] Done: pi_contracts added loading_port / price_term / invoice_to columns")


def downgrade():
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE pi_contracts DROP COLUMN IF EXISTS loading_port"))
        conn.execute(text("ALTER TABLE pi_contracts DROP COLUMN IF EXISTS price_term"))
        conn.execute(text("ALTER TABLE pi_contracts DROP COLUMN IF EXISTS invoice_to"))
        conn.commit()
    print("[006] Downgrade: SQLite does not support real DROP COLUMN")