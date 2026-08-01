"""
迁移 018: 将 references/ 下的静态数据 JSON 与 backend/data/users.json 迁入 SQLite

数据来源:
    references/packaging_data.json          → packaging_types / pallets / container_specs
    references/customs_codes.json           → products_knowledge (合并, components→customs_ingredients)
    references/申报要素.json                  → declaration_elements
    references/ingredient_mapping.json      → ingredient_mappings
    references/products_name_mapping.json   → translation_mappings (product_name)
    references/appearance_color_mapping.json → translation_mappings (appearance)
    references/ion_type_mapping.json        → translation_mappings (ion_type)
    references/msds_english_template.json   → msds_templates
    backend/data/users.json                 → users

运行方式:
    cd backend && python -c "
        exec(open('migrations/018_migrate_json_to_db.py').read())
    "
"""
import json

from sqlalchemy import text

import app.models  # noqa: F401  注册全部模型到 Base.metadata
from app.core.config import ROOT
from app.database import Base, engine, SessionLocal
from app.models.order import PackagingType, ProductKnowledge
from app.models.reference_data import (
    Pallet,
    ContainerSpec,
    DeclarationElement,
    IngredientMapping,
    TranslationMapping,
    MsdsTemplate,
)
from app.models.user import User

REFERENCES_DIR = ROOT / "references"
USERS_JSON = ROOT / "backend" / "data" / "users.json"


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_column(table: str, column_def: str):
    """幂等加列：列已存在则跳过"""
    col_name = column_def.split()[0]
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))]
        if col_name in cols:
            print(f"  [alter] {table}.{col_name} 已存在, 跳过")
            return
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_def}"))
        conn.commit()
        print(f"  [alter] {table} + {column_def}")


def seed_products_knowledge(db):
    """customs_codes.json → products_knowledge (按 internal_code upsert)"""
    data = _load_json(REFERENCES_DIR / "customs_codes.json")
    added = updated = skipped = 0
    seen = set()
    for r in data:
        ic = (r.get("internal_code") or "").strip()
        if not ic or ic in seen:
            skipped += 1
            continue
        seen.add(ic)
        rec = db.query(ProductKnowledge).filter_by(internal_code=ic).first()
        if rec is None:
            rec = ProductKnowledge(internal_code=ic)
            db.add(rec)
            added += 1
        else:
            updated += 1
        rec.hs_code = r.get("product_code")
        rec.customs_name = r.get("customs_name")
        rec.customs_ingredients = r.get("components")
        rec.product_appearance = r.get("product_appearance")
    db.commit()
    print(f"[seed] products_knowledge: added={added}, updated={updated}, skipped={skipped}")


def seed_packaging_types(db):
    """packaging_data.json.packages → packaging_types (覆盖过期行, 清理孤儿行)"""
    data = _load_json(REFERENCES_DIR / "packaging_data.json")
    json_names = [pkg["name"] for pkg in data["packages"]]
    count = 0
    for pkg in data["packages"]:
        rec = db.query(PackagingType).filter_by(name=pkg["name"]).first()
        if rec is None:
            rec = PackagingType(name=pkg["name"])
            db.add(rec)
        rec.dims = pkg.get("dims")
        rec.cbm = pkg.get("cbm")
        rec.tare_kg = pkg.get("tare_kg")
        rec.gross_kg = pkg.get("gross_kg")
        rec.net_kg = pkg.get("net_kg")
        rec.barrel_type = pkg.get("barrel_type")
        rec.is_palletizable = 1 if pkg.get("is_palletizable") else 0
        rec.no_pallet_qty = pkg.get("no_pallet_qty")
        rec.pallet_qty_1x1 = pkg.get("pallet_qty_1x1")
        rec.pallet_qty_1_1x1_1 = pkg.get("pallet_qty_1_1x1_1")
        count += 1
    # 清理 JSON 中已不存在的过期包装类型（如旧名 "1吨桶"）
    stale = db.query(PackagingType).filter(~PackagingType.name.in_(json_names)).all()
    for rec in stale:
        db.delete(rec)
        print(f"  [cleanup] packaging_types 删除过期行: {rec.name}")
    db.commit()
    print(f"[seed] packaging_types: {count} upserted, {len(stale)} stale deleted")


def seed_pallets(db):
    """packaging_data.json.pallets → pallets"""
    data = _load_json(REFERENCES_DIR / "packaging_data.json")
    count = 0
    for p in data["pallets"]:
        rec = db.query(Pallet).filter_by(name=p["name"]).first()
        if rec is None:
            rec = Pallet(name=p["name"])
            db.add(rec)
        rec.dims = p.get("dims")
        rec.weight_kg = p.get("weight_kg")
        rec.cbm = p.get("cbm")
        count += 1
    db.commit()
    print(f"[seed] pallets: {count} upserted")


def seed_container_specs(db):
    """packaging_data.json container_20gp/40gp → container_specs"""
    data = _load_json(REFERENCES_DIR / "packaging_data.json")
    count = 0
    for name, key in [("20GP", "container_20gp"), ("40GP", "container_40gp")]:
        c = data[key]
        rec = db.query(ContainerSpec).filter_by(name=name).first()
        if rec is None:
            rec = ContainerSpec(name=name)
            db.add(rec)
        rec.max_cbm = c.get("max_cbm")
        rec.max_weight_kg = c.get("max_weight_kg")
        count += 1
    db.commit()
    print(f"[seed] container_specs: {count} upserted")


def seed_declaration_elements(db):
    """申报要素.json → declaration_elements"""
    data = _load_json(REFERENCES_DIR / "申报要素.json")
    count = 0
    for key, item in data.items():
        if "|" in key:
            hs_code, dname = key.split("|", 1)
        else:
            hs_code, dname = item.get("hs_code", ""), item.get("申报名称", "")
        if not hs_code or not dname:
            continue
        rec = db.query(DeclarationElement).filter_by(hs_code=hs_code, declaration_name=dname).first()
        if rec is None:
            db.add(DeclarationElement(
                hs_code=hs_code,
                declaration_name=dname,
                elements_text=item.get("申报要素", ""),
            ))
            count += 1
    db.commit()
    print(f"[seed] declaration_elements: {count} inserted")


def seed_ingredient_mappings(db):
    """ingredient_mapping.json → ingredient_mappings (表非空则跳过)"""
    if db.query(IngredientMapping).count() > 0:
        print("[seed] ingredient_mappings 已有数据, 跳过")
        return
    data = _load_json(REFERENCES_DIR / "ingredient_mapping.json")
    for m in data.get("mappings", []):
        db.add(IngredientMapping(
            cn_names=json.dumps(m.get("cn_names", []), ensure_ascii=False),
            en_names=json.dumps(m.get("en_names", []), ensure_ascii=False),
            cas_numbers=json.dumps(m.get("cas_numbers", []), ensure_ascii=False),
            raw=m.get("raw"),
        ))
    db.commit()
    print(f"[seed] ingredient_mappings: {len(data.get('mappings', []))} inserted")


def seed_translation_mappings(db):
    """三个 cn/en 映射文件 → translation_mappings (mapping_type 区分)"""
    mapping_files = {
        "product_name": "products_name_mapping.json",
        "appearance": "appearance_color_mapping.json",
        "ion_type": "ion_type_mapping.json",
    }
    for mtype, fname in mapping_files.items():
        fpath = REFERENCES_DIR / fname
        if not fpath.exists():
            print(f"  [warn] 缺少 {fname}, 跳过")
            continue
        data = _load_json(fpath)
        count = 0
        seen = set()
        for item in data.get("mappings", []):
            cn, en = item.get("cn"), item.get("en")
            if not cn or not en:
                continue
            key = (mtype, cn)
            if key in seen:
                continue  # 同文件内去重
            seen.add(key)
            exists = db.query(TranslationMapping).filter_by(mapping_type=mtype, cn=cn).first()
            if exists:
                continue
            db.add(TranslationMapping(mapping_type=mtype, cn=cn, en=en))
            count += 1
        db.commit()
        print(f"[seed] translation_mappings[{mtype}]: {count} inserted")
    total = db.query(TranslationMapping).count()
    print(f"  translation_mappings total: {total}")


def seed_msds_templates(db):
    """msds_english_template.json → msds_templates (name=english)"""
    if db.query(MsdsTemplate).filter_by(name="english").first():
        print("[seed] msds_templates english 已存在, 跳过")
        return
    data = _load_json(REFERENCES_DIR / "msds_english_template.json")
    db.add(MsdsTemplate(name="english", template_json=json.dumps(data, ensure_ascii=False)))
    db.commit()
    print("[seed] msds_templates: 1 inserted")


def seed_users(db):
    """backend/data/users.json → users (保持明文)"""
    data = _load_json(USERS_JSON)
    count = 0
    for u in data:
        name = (u.get("name") or "").strip()
        password = u.get("password") or ""
        if not name:
            continue
        rec = db.query(User).filter_by(name=name).first()
        if rec is None:
            rec = User(name=name)
            db.add(rec)
        rec.password = password
        count += 1
    db.commit()
    print(f"[seed] users: {count} upserted")


def verify_counts():
    db = SessionLocal()
    try:
        for model in [
            PackagingType, Pallet, ContainerSpec, ProductKnowledge,
            DeclarationElement, IngredientMapping, TranslationMapping,
            MsdsTemplate, User,
        ]:
            print(f"  {model.__tablename__}: {db.query(model).count()}")
    finally:
        db.close()


def upgrade():
    Base.metadata.create_all(bind=engine)
    ensure_column("packaging_types", "is_palletizable INTEGER DEFAULT 1")
    ensure_column("products_knowledge", "product_appearance TEXT")

    db = SessionLocal()
    try:
        seed_products_knowledge(db)
        seed_packaging_types(db)
        seed_pallets(db)
        seed_container_specs(db)
        seed_declaration_elements(db)
        seed_ingredient_mappings(db)
        seed_translation_mappings(db)
        seed_msds_templates(db)
        seed_users(db)
    finally:
        db.close()

    print("\n[018] 迁移后行数:")
    verify_counts()
    print("[018] Done")


def downgrade():
    """删除新表与新增列（SQLite >= 3.35 支持 DROP COLUMN）"""
    for model in [User, MsdsTemplate, TranslationMapping, IngredientMapping,
                  DeclarationElement, ContainerSpec, Pallet]:
        model.__table__.drop(bind=engine, checkfirst=True)
        print(f"[018] dropped {model.__tablename__}")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE packaging_types DROP COLUMN is_palletizable"))
        conn.execute(text("ALTER TABLE products_knowledge DROP COLUMN product_appearance"))
        conn.commit()
    print("[018] Downgrade done")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
