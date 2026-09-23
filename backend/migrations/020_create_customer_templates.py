"""Create customer_templates table (clearance per-customer templates)."""
from sqlalchemy import text

from app.database import engine


def migrate():
    with engine.connect() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS customer_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_code VARCHAR(50) NOT NULL,
                doc_type VARCHAR(20) NOT NULL,
                company_code VARCHAR(20),
                template_blob BLOB NOT NULL,
                options_json TEXT,
                file_name VARCHAR(200),
                version INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                created_by VARCHAR(50),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_customer_templates_key "
                "ON customer_templates(customer_code, doc_type, is_active)"
            )
        )
        conn.commit()
        print("[migration] customer_templates created")


if __name__ == "__main__":
    migrate()
