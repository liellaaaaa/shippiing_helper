"""
迁移 007: 从 Excel 参考表加载 products_knowledge 数据（H.S.Code / 报关品名）

运行方式:
    cd backend && python -c "
        exec(open('migrations/007_seed_products_knowledge.py').read())
    "
"""
import openpyxl
import zipfile
import re
import os
from pathlib import Path
from app.database import engine, SessionLocal
from app.models.order import ProductKnowledge


def get_shared_strings(xlsx_path):
    """从 xlsx 文件提取共享字符串列表"""
    with zipfile.ZipFile(xlsx_path, 'r') as z:
        ss_xml = z.read('xl/sharedStrings.xml').decode('utf-8')
    return re.findall(r'<t[^>]*>([^<]*)</t>', ss_xml)


def load_products_from_excel(xlsx_path):
    """从 Excel 读取产品知识数据"""
    texts = get_shared_strings(xlsx_path)

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active

    products = []
    for row in ws.iter_rows(min_row=2):
        vals = []
        for cell in row[:14]:
            if cell.value is not None:
                vals.append(cell.value)
            elif cell.data_type == 's':
                idx = cell.value
                vals.append(texts[idx] if idx < len(texts) else '')
            else:
                vals.append(None)

        internal_code = vals[1] if len(vals) > 1 else None
        if not internal_code or not isinstance(internal_code, str):
            continue

        hs_code = str(vals[6]).strip() if len(vals) > 6 and vals[6] else None
        customs_name = vals[7].strip() if len(vals) > 7 and vals[7] else None
        product_name_cn = None # not in this file
        product_name_en = None

        products.append({
            'internal_code': internal_code.strip(),
            'hs_code': hs_code,
            'customs_name': customs_name,
            'product_name_cn': product_name_cn,
            'product_name_en': product_name_en,
        })

    wb.close()
    return products


def upgrade():
    """加载 Excel 数据到 products_knowledge 表"""
    # Use environment variable or default to references directory relative to project root
    xlsx_path = os.getenv("EXPORT_CODES_FILE", str(Path(__file__).parent.parent.parent / "references" / "2024.12.5 最新出口商品编码及报关成分.xlsx"))
    print(f'Reading: {xlsx_path}')

    products = load_products_from_excel(xlsx_path)
    print(f'Loaded {len(products)} products from Excel')

    db = SessionLocal()
    try:
        # 统计现有数据
        existing = db.query(ProductKnowledge).count()
        print(f'Existing products_knowledge: {existing}')

        added = 0
        updated = 0
        seen = set()
        for p in products:
            if not p['internal_code']:
                continue
            if p['internal_code'] in seen:
                continue  # Skip duplicates
            seen.add(p['internal_code'])
            existing_rec = db.query(ProductKnowledge).filter_by(
                internal_code=p['internal_code']
            ).first()

            if existing_rec:
                # 更新 H.S.Code（如果已有记录）
                if p['hs_code']:
                    existing_rec.hs_code = p['hs_code']
                if p['customs_name']:
                    existing_rec.customs_name = p['customs_name']
                updated += 1
            else:
                rec = ProductKnowledge(
                    internal_code=p['internal_code'],
                    hs_code=p['hs_code'],
                    customs_name=p['customs_name'],
                )
                db.add(rec)
                added += 1

        db.commit()
        print(f'Added: {added}, Updated: {updated}')

        # 验证
        final_count = db.query(ProductKnowledge).count()
        print(f'Final products_knowledge count: {final_count}')

    finally:
        db.close()

    print('[007] Done: products_knowledge seeded from Excel')


def downgrade():
    """清空 products_knowledge 表"""
    db = SessionLocal()
    try:
        db.query(ProductKnowledge).delete()
        db.commit()
        print('[007] Downgrade: products_knowledge cleared')
    finally:
        db.close()


if __name__ == '__main__':
    upgrade()