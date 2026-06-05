"""Create msds_corrections table for correction history."""
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
        CREATE TABLE IF NOT EXISTS msds_corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            msds_index_id INTEGER NOT NULL,
            file_format VARCHAR(10),
            upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            product_name VARCHAR(200),
            corrected_by VARCHAR(100),
            original_filename VARCHAR(255),
            new_filename VARCHAR(255)
        )
    """)
    conn.commit()
    print("Created msds_corrections table")
    conn.close()

def downgrade():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS msds_corrections")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade()