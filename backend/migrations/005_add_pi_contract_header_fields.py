"""
迁移 005: 给 pi_contracts 表新增 consignee_name / consignee_address / destination 字段
"""

from sqlalchemy import text
from app.database import engine


def upgrade():
    with engine.connect() as conn:
        # 检查列是否已存在（幂等）
        existing = conn.execute(text("PRAGMA table_info(pi_contracts)")).fetchall()
        col_names = [row[1] for row in existing]

        if "consignee_name" not in col_names:
            conn.execute(text("ALTER TABLE pi_contracts ADD COLUMN consignee_name TEXT"))
        if "consignee_address" not in col_names:
            conn.execute(text("ALTER TABLE pi_contracts ADD COLUMN consignee_address TEXT"))
        if "destination" not in col_names:
            conn.execute(text("ALTER TABLE pi_contracts ADD COLUMN destination TEXT"))

        # 更新 pi_contract_items.internal_code 约束为允许 NULL（Proforma格式无编码）
        conn.execute(text("DROP INDEX IF EXISTS idx_pi_contract_items_internal_code"))
        conn.execute(text("ALTER TABLE pi_contract_items MODIFY COLUMN internal_code TEXT"))

        conn.commit()
    print("✅ 005 完成: pi_contracts 新增 3 列 + pi_contract_items.internal_code 允许 NULL")


def downgrade():
    with engine.connect() as conn:
        # SQLite 不支持 DROP COLUMN，标记为已废弃
        conn.execute("ALTER TABLE pi_contracts DROP COLUMN IF EXISTS consignee_name")
        conn.execute("ALTER TABLE pi_contracts DROP COLUMN IF EXISTS consignee_address")
        conn.execute("ALTER TABLE pi_contracts DROP COLUMN IF EXISTS destination")
        conn.commit()
    print("⚠️  downgrade: SQLite 不支持真正删除列")