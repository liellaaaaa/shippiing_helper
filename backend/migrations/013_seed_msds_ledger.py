"""Seed msds_product_ledger from old MSDS files."""
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models.msds_ledger import MsdsLedger
from app.services.msds_generator_service import MSDSGeneratorService
from app.core.config import MSDS_DIR


def seed():
    db = SessionLocal()
    gen_svc = MSDSGeneratorService()
    count = 0

    msds_dir = Path(MSDS_DIR)
    if not msds_dir.exists():
        print(f"[seed] MSDS directory not found: {MSDS_DIR}")
        return

    # Only process Chinese MSDS files (.docx)
    for f in msds_dir.glob("*.docx"):
        if f.name.startswith("~$") or f.name.startswith("模板") or f.name.startswith("test"):
            continue
        if "英文" in f.name or "MSDS for" in f.name:
            continue

        try:
            data = gen_svc.parse_msds_file(str(f))
            product_name = data.get("product_name", "")
            if not product_name:
                continue

            # Check if already exists
            existing = db.query(MsdsLedger).filter(
                MsdsLedger.customs_name == product_name
            ).first()
            if existing:
                print(f"[seed] Skip (exists): {product_name}")
                continue

            # Create new ledger entry
            composition = data.get("composition", [])
            composition_data = []
            for c in composition:
                composition_data.append({
                    "component_cn": c.get("component_cn", ""),
                    "component_en": "",
                    "cas": c.get("cas", ""),
                    "percentage": c.get("percentage", ""),
                })

            pc = data.get("physicochemical", {})
            from datetime import datetime
            now = datetime.utcnow()
            ledger = MsdsLedger(
                internal_code="",
                customs_name=product_name,
                appearance=pc.get("physical_form", ""),
                ion_type=pc.get("ion_type", ""),
                ph=pc.get("ph", ""),
                composition=composition_data,
                product_name_en="",
                appearance_en="",
                ion_type_en="",
                version=1,
                created_at=now,
                updated_at=now,
            )
            db.add(ledger)
            count += 1
            print(f"[seed] Added: {product_name}")
        except Exception as e:
            print(f"[seed] Error processing {f.name}: {e}")

    db.commit()
    db.close()
    print(f"[seed] Done. Added {count} entries.")


if __name__ == "__main__":
    seed()
