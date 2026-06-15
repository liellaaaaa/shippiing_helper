"""一次性脚本：从 Excel 提取商品编码数据生成 JSON"""
import json
import openpyxl

INPUT_FILE = "references/2024.12.5 最新出口商品编码及报关成分.xlsx"
OUTPUT_FILE = "references/customs_codes.json"

# 列索引（基于表头行，0-based）
# 表头：序号(0) | 产品内编(1) | PI名建议(2) | 产品线(3) | 产品外观(4) | 旧商品编码(5) | 新商品编码(6) | 报关名称(7) | 退税税率(8) | 监管条件(9) | 检验检疫(10) | 成分(11)
COLS = {
    "internal_code": 1,
    "product_code": 6,       # 新商品编码
    "customs_name": 7,       # 报关名称
    "components": 10,       # 成分
    "product_appearance": 4,
}

def extract():
    wb = openpyxl.load_workbook(INPUT_FILE, data_only=True)
    ws = wb.active

    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):  # skip header
        if not row[COLS["internal_code"]]:
            continue
        record = {
            "internal_code": str(row[COLS["internal_code"]] or "").strip(),
            "product_code": str(row[COLS["product_code"]] or "").strip(),
            "customs_name": str(row[COLS["customs_name"]] or "").strip(),
            "components": str(row[COLS["components"]] or "").strip(),
            "product_appearance": str(row[COLS["product_appearance"]] or "").strip(),
        }
        records.append(record)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"Extracted {len(records)} records to {OUTPUT_FILE}")

if __name__ == "__main__":
    extract()