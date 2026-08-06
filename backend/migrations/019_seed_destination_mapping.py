"""
迁移 019: 将港口/国家中英文对照写入 translation_mappings 表

数据来源: app/core/destination_map.py 的 CITY_CN_MAP / COUNTRY_CN_MAP
    mapping_type='destination_city'    → 港口/城市 en→cn
    mapping_type='destination_country' → 国家 en→cn
同一中文对应多个英文别名时仅取第一个，其余别名由内置字典回退解析。

运行方式:
    cd backend && python -c "
        exec(open('migrations/019_seed_destination_mapping.py').read())
    "
"""
from app.core.destination_map import CITY_CN_MAP, COUNTRY_CN_MAP
from app.database import SessionLocal
from app.models.reference_data import TranslationMapping


def seed_destination_mapping(db):
    inserted = skipped = 0
    for mapping_type, source in (
        ("destination_city", CITY_CN_MAP),
        ("destination_country", COUNTRY_CN_MAP),
    ):
        seen_cn = set()
        for en, cn in source.items():
            if cn in seen_cn:
                continue  # 同一中文只存第一个英文别名
            seen_cn.add(cn)
            exists = db.query(TranslationMapping).filter_by(mapping_type=mapping_type, cn=cn).first()
            if exists:
                skipped += 1
                continue
            db.add(TranslationMapping(mapping_type=mapping_type, cn=cn, en=en))
            inserted += 1
    db.commit()
    print(f"[seed] destination mapping: {inserted} inserted, {skipped} skipped (dup/已存在)")


def upgrade():
    db = SessionLocal()
    try:
        seed_destination_mapping(db)
    finally:
        db.close()
    print("[019] Done")


if __name__ == "__main__":
    upgrade()
