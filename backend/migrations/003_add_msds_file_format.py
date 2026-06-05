"""Add file_format column to msds_indexes table."""
import sqlite3
import os

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "shipping_helper.db"
)

def upgrade():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Check if column already exists
    cur.execute("PRAGMA table_info(msds_indexes)")
    cols = [row[1] for row in cur.fetchall()]
    if "file_format" not in cols:
        cur.execute("ALTER TABLE msds_indexes ADD COLUMN file_format VARCHAR(10)")
        conn.commit()
        print("Added file_format column to msds_indexes")
    else:
        print("file_format column already exists")
    conn.close()

def downgrade():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("ALTER TABLE msds_indexes DROP COLUMN file_format")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade()
