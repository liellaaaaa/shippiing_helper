"""Create msds_product_ledger table."""
from sqlalchemy import text
from app.database import engine


def migrate():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS msds_product_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                internal_code VARCHAR(100) NOT NULL,
                customs_name VARCHAR(200),
                appearance VARCHAR(500),
                ion_type VARCHAR(50),
                ph VARCHAR(50),
                composition JSON,
                product_name_en VARCHAR(200),
                appearance_en VARCHAR(500),
                ion_type_en VARCHAR(50),
                version INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_msds_ledger_internal_code ON msds_product_ledger(internal_code)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_msds_ledger_customs_name ON msds_product_ledger(customs_name)"""))
        conn.commit()
        print("[migration] msds_product_ledger created")


if __name__ == "__main__":
    migrate()
