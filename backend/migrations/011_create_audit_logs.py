"""Create audit_logs table for user behavior tracking."""
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
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type VARCHAR(50) NOT NULL,
            user_name VARCHAR(100) NOT NULL,
            module VARCHAR(50),
            action_time DATETIME NOT NULL,
            detail TEXT,
            ip_address VARCHAR(50),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action_time ON audit_logs(action_time)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_name ON audit_logs(user_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type)")

    conn.commit()
    print("Migration 011 complete: created audit_logs table")
    conn.close()

def downgrade():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS audit_logs")
    conn.commit()
    print("Migration 011 rolled back")
    conn.close()

if __name__ == "__main__":
    upgrade()
