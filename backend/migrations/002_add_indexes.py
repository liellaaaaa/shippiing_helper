"""Add indexes for pi_contracts and pi_contract_items."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "shipping_helper.db")


def upgrade():
    """Create indexes for PI tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Unique index on pi_contracts.pi_no
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_pi_contracts_pi_no ON pi_contracts(pi_no)
    """)

    # Index on pi_contract_items.internal_code for fast lookup
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pi_contract_items_internal_code ON pi_contract_items(internal_code)
    """)

    # Index on pi_contract_items.pi_contract_id (for FK lookups)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pi_contract_items_contract_id ON pi_contract_items(pi_contract_id)
    """)

    # Unique index on pi_data.internal_code
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_pi_data_internal_code ON pi_data(internal_code)
    """)

    conn.commit()
    conn.close()
    print("Migration 002: indexes created successfully")


def downgrade():
    """Drop all indexes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DROP INDEX IF EXISTS idx_pi_contracts_pi_no")
    cursor.execute("DROP INDEX IF EXISTS idx_pi_contract_items_internal_code")
    cursor.execute("DROP INDEX IF EXISTS idx_pi_contract_items_contract_id")
    cursor.execute("DROP INDEX IF EXISTS idx_pi_data_internal_code")

    conn.commit()
    conn.close()
    print("Migration 002: indexes dropped")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()