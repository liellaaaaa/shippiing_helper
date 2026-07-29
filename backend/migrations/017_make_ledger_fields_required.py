"""Migration 017: make ledger fields NOT NULL, drop internal_code."""
from sqlalchemy import text
from app.database import engine


def migrate():
    with engine.connect() as conn:
        # SQLite doesn't support DROP COLUMN directly before 3.35.5,
        # but supports ALTER TABLE ... DROP COLUMN since 3.35.0.
        # We use the supported approach:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS msds_product_ledger_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customs_name VARCHAR(200) NOT NULL,
                appearance VARCHAR(500) NOT NULL,
                ion_type VARCHAR(50) NOT NULL,
                ph VARCHAR(50) NOT NULL,
                composition JSON NOT NULL DEFAULT '[]',
                product_name_en VARCHAR(200),
                appearance_en VARCHAR(500),
                ion_type_en VARCHAR(50),
                version INTEGER DEFAULT 1,
                created_at DATETIME,
                updated_at DATETIME
            )
        """))
        conn.execute(text("""
            INSERT INTO msds_product_ledger_new (
                id, customs_name, appearance, ion_type, ph, composition,
                product_name_en, appearance_en, ion_type_en,
                version, created_at, updated_at
            )
            SELECT
                id, COALESCE(customs_name, ''), COALESCE(appearance, ''),
                COALESCE(ion_type, ''), COALESCE(ph, ''),
                COALESCE(composition, '[]'),
                product_name_en, appearance_en, ion_type_en,
                version, created_at, updated_at
            FROM msds_product_ledger
        """))
        conn.execute(text("DROP TABLE msds_product_ledger"))
        conn.execute(text("ALTER TABLE msds_product_ledger_new RENAME TO msds_product_ledger"))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_msds_ledger_customs_name
            ON msds_product_ledger(customs_name)
        """))
        conn.commit()
        print("[migration] 017: msds_product_ledger columns updated")


if __name__ == "__main__":
    migrate()
