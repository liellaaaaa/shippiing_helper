"""Create transport_reports table for 海运鉴定报告 index."""
import sqlite3
import os

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "shipping_helper.db"
)

def upgrade():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transport_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename VARCHAR(255) NOT NULL UNIQUE,
            file_path VARCHAR(500) NOT NULL,
            file_format VARCHAR(10) DEFAULT 'pdf',
            loaded INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    print("Created transport_reports table")
    conn.close()

def downgrade():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS transport_reports")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade()
