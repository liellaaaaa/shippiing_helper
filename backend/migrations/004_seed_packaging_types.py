"""Seed packaging_types and pallets tables from packaging_data.json"""

import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "shipping_helper.db")
PACKAGING_JSON = os.path.join(os.path.dirname(__file__), "..", "..", "..", "参考", "knowledge", "packaging_data.json")


def upgrade():
    """Seed packaging_types from JSON."""
    import sqlite3

    with open(PACKAGING_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Insert packaging types
    for pkg in data["packages"]:
        cursor.execute("""
            INSERT OR IGNORE INTO packaging_types
            (name, dims, cbm, tare_kg, gross_kg, net_kg, pallet_qty_1x1, pallet_qty_1_1x1_1, no_pallet_qty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pkg["name"],
            pkg.get("dims"),
            pkg.get("cbm"),
            pkg.get("tare_kg"),
            pkg.get("gross_kg"),
            pkg.get("net_kg"),
            data["pallet_capacity"].get(pkg["name"], {}).get("1.0*1.0"),
            data["pallet_capacity"].get(pkg["name"], {}).get("1.1*1.1"),
            data["no_pallet_container_capacity"].get(pkg["name"]),
        ))

    conn.commit()
    conn.close()
    print("Migration 004: packaging_types seeded successfully")


def downgrade():
    """Clear packaging_types."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM packaging_types")
    conn.commit()
    conn.close()
    print("Migration 004: packaging_types cleared")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()