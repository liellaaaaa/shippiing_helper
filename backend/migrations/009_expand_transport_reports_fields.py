"""Expand transport_reports table with extracted fields + create junction table."""
import sqlite3
import os

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "shipping_helper.db"
)

def upgrade():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Add extracted fields to transport_reports
    for col, col_type in [
        ("report_no",          "VARCHAR(100)"),
        ("product_name_cn",    "VARCHAR(255)"),
        ("product_name_en",    "VARCHAR(255)"),
        ("sample_desc_cn",     "VARCHAR(500)"),
        ("sample_desc_en",     "VARCHAR(500)"),
    ]:
        cur.execute(f"ALTER TABLE transport_reports ADD COLUMN {col} {col_type}")

    # 2. Create junction table: order_item <-> transport_report
    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_item_transport_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_item_id INTEGER NOT NULL,
            transport_report_id INTEGER NOT NULL,
            link_order INTEGER DEFAULT 0,
            linked_at TEXT DEFAULT (datetime('now')),
            UNIQUE(order_item_id, transport_report_id)
        )
    """)
    conn.commit()
    print("Migration 009 complete: expanded transport_reports + created junction table")
    conn.close()

def downgrade():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS order_item_transport_reports")
    for col in ["report_no", "product_name_cn", "product_name_en", "sample_desc_cn", "sample_desc_en"]:
        # SQLite doesn't support DROP COLUMN easily; recreate table would be needed.
        # For simplicity just note columns remain — in production use full schema rebuild.
        pass
    conn.commit()
    print("Migration 009 rolled back (columns remain — SQLite limitation)")
    conn.close()

if __name__ == "__main__":
    upgrade()
