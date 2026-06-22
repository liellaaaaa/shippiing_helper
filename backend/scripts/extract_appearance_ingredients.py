"""
从用户提供的数据文本中提取外观颜色和报关成分对照，写入 JSON 文件。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent / "references"

# ============ 外观颜色数据（41条）============
APPEARANCE_COLORS_RAW = """
黄色液体 — Yellow liquid
白色粉末 — White powder
微黄色液体 — Light yellow liquid
浅黄色液体 — Pale yellow liquid
棕黑色液体 — Brownish black liquid
无色至黄色透明液体 — Colorless to yellow transparent liquid
微黄色粉末 — Light yellow powder
微黄色片状物 — Light yellow flakes
无色透明液 — Colorless transparent liquid
黄色粘稠液体 — Yellow viscous liquid
无色液体 — Colorless liquid
白色不透明液体 — White opaque liquid
微黄色粘稠液体 — Light yellow viscous liquid
微黄色粘稠粘液 — Light yellow viscous mucus
类白色液体 — Off-white liquid
棕黑色粘稠液体 — Brownish black viscous liquid
浅黄色粘稠液体 — Pale yellow viscous liquid
无色透明液体 — Colorless transparent liquid
黄色粉末 — Yellow powder
淡黄色片状颗粒 — Pale yellow flaky particles
类白色糊状 — Off-white paste
淡黄色液体 — Pale yellow liquid
类白色粘稠液体 — Off-white viscous liquid
黄色透明液 — Yellow transparent liquid
淡黄色透明液体 — Pale yellow transparent liquid
无色半透明液体 — Colorless translucent liquid
黄色透明液体 — Yellow transparent liquid
白色液体 — White liquid
微黄色块状 — Light yellow lumps
棕黑色透明液 — Brownish black transparent liquid
蓝色透明液体 — Blue transparent liquid
类白色透明液体 — Off-white transparent liquid
微黄色碎片 — Light yellow fragments
黄色透明粘液 — Yellow transparent mucus
微黄色膏体 — Light yellow ointment
无色至黄色液体 — Colorless to yellow liquid
棕黑色液体 — Brownish black liquid
棕黄色粘稠液体 — Brownish yellow viscous liquid
类白色固体 — Off-white solid
蓝色液体 — Blue liquid
微黄色透明液体 — Light yellow transparent liquid
""".strip()

# ============ 报关成分数据（42条）============
INGREDIENTS_RAW = """
聚二甲基硅氧烷（硅油）9016-00-6 — Polydimethylsiloxane (Silicone Oil), CAS:9016-00-6
非离子乳化剂 68213-23-0 — Nonionic Emulsifier, CAS:68213-23-0
水 7732-18-5 — Water, CAS:7732-18-5
元明粉 7757-82-6 — Sodium Sulfate Anhydrous, CAS:7757-82-6
葡萄糖酸钠 527-07-1 / 41859-67-0 — Sodium Gluconate, CAS:527-07-1 / 41859-67-0
轻质碱 497-19-8 — Sodium Carbonate (Light Soda Ash), CAS:497-19-8
乙二醇二醋酸酯 111-55-7 — Ethylene Glycol Diacetate, CAS:111-55-7
非离子表面活性剂 68603-25-8 — Nonionic Surfactant, CAS:68603-25-8
聚乙二醇 25322-68-3 — Polyethylene Glycol, CAS:25322-68-3
酚醛树脂 9003-35-4 — Phenolic Resin, CAS:9003-35-4
分散剂 NNO 26545-58-4 / 9084-06-04 — Dispersant NNO, CAS:26545-58-4 / 9084-06-04
柠檬酸钠 68-04-2 — Sodium Citrate, CAS:68-04-2
中性纤维素酶 9012-54-8 — Neutral Cellulase, CAS:9012-54-8
山梨糖醇 50-70-4；山梨糖醇液 — Sorbitol / Sorbitol Liquid, CAS:50-70-4
脂肪醇聚氧烷基醚 68439-46-3 — Fatty Alcohol Alkoxylate, CAS:68439-46-3
端环氧硅油 9004-73-3；聚醚环氧硅油 — Epoxy Terminated Silicone Oil / Polyether Epoxy Silicone Oil, CAS:9004-73-3
聚合物 PMA-60 26677-99-6 — Polymer PMA-60, CAS:26677-99-6
柔软剂；亲水软油 68153-35-5；阳离子柔软剂 — Softener / Hydrophilic Soft Oil / Cationic Softener, CAS:68153-35-5
葡萄糖 50-99-7 — Dextrose (Glucose), CAS:50-99-7
二甲基二烯丙基氯化铵 26062-79-3 — Dimethyl Diallyl Ammonium Chloride, CAS:26062-79-3
异构十三醇聚氧乙烯醚 9043-30-5 — Isotridecanol Ethoxylate, CAS:9043-30-5
丙三醇（甘油）56-81-5 — Glycerin (Glycerol), CAS:56-81-5
柔软吸湿排汗整理剂 9016-88-0 — Soft Moisture Absorption & Sweat Wicking Finishing Agent, CAS:9016-88-0
聚硅氧烷 63148-62-9 — Polysiloxane, CAS:63148-62-9
聚乙二醇单油酸酯 9004-96-0 — Polyethylene Glycol Monooleate, CAS:9004-96-0
水性聚氨酯；聚氨酯 9009-54-5 — Waterborne Polyurethane / Polyurethane, CAS:9009-54-5
软片 67701-03-5 — Soft Flakes, CAS:67701-03-5
聚乙烯醇 9002-89-5 — Polyvinyl Alcohol (PVA), CAS:9002-89-5
柠檬酸 77-92-9 — Citric Acid, CAS:77-92-9
聚丙烯酸酯 25608-33-7；聚丙烯酸脂 9003-01-4 — Polyacrylate, CAS:25608-33-7 / 9003-01-4
丙烯酸酯共聚物 — Acrylate Copolymer
丙烯酸氟烷基醋共聚物 65605-70-1；无氟防水剂 65605-70-1 — Fluoroalkyl Acrylate Copolymer / Fluorine-Free Water Repellent Agent, CAS:65605-70-1
双酚 S 80-09-1 — Bisphenol S, CAS:80-09-1
烯基聚醚改性有机硅聚合物 68937-55-3 — Alkenyl Polyether Modified Silicone Polymer, CAS:68937-55-3
丙二醇苯醚 770-35-4 — Propylene Glycol Phenyl Ether, CAS:770-35-4
油酸 112-80-1 — Oleic Acid, CAS:112-80-1
二甘醇 111-46-6 — Diethylene Glycol, CAS:111-46-6
三聚磷酸钠 7758-29-4 — Sodium Tripolyphosphate, CAS:7758-29-4
HX 多功能整理剂 52591-27-2 — HX Multi-functional Finishing Agent, CAS:52591-27-2
乙烯基杂环改性聚合物 29297-55-0 — Vinyl Heterocycle Modified Polymer, CAS:29297-55-0
脂肪醇聚氧乙烯醚 52292-17-8 — Fatty Alcohol Ethoxylate, CAS:52292-17-8
十二烷基苯磺酸钠 25155-30-0 — Sodium Dodecyl Benzene Sulfonate, CAS:25155-30-0
""".strip()

SEPARATOR = " — "
CAS_PATTERN = re.compile(r"\b\d{2,7}-\d{2,7}(?:-\d+)?\b")


def parse_appearance_colors():
    """解析外观颜色：按 ' — ' 分割"""
    mappings = []
    for line in APPEARANCE_COLORS_RAW.split("\n"):
        line = line.strip()
        if not line or SEPARATOR not in line:
            continue
        parts = line.split(SEPARATOR, 1)
        cn = parts[0].strip()
        en = parts[1].strip()
        mappings.append({"cn": cn, "en": en})
    return mappings


def parse_ingredients():
    """解析报关成分：提取 CAS 号，分离中英文别名"""
    mappings = []
    for line in INGREDIENTS_RAW.split("\n"):
        line = line.strip()
        if not line or SEPARATOR not in line:
            continue

        raw = line
        left, right = line.split(SEPARATOR, 1)

        # 提取中文部分中的 CAS 号
        left_cas = CAS_PATTERN.findall(left)
        # 提取英文部分中的 CAS 号（CAS: 前缀格式）
        right_cas = CAS_PATTERN.findall(right)
        all_cas = list(dict.fromkeys(left_cas + right_cas))  # 去重保持顺序

        # 去掉 CAS 号后的中文部分（剩余为品名）
        cn_part = CAS_PATTERN.sub("", left).strip()
        # 中文别名分隔符：； 或 /
        cn_names = [n.strip() for n in re.split(r"[；/]", cn_part) if n.strip()]

        # 去掉 CAS: 标签后的英文部分，再去掉残留的独立 CAS 号
        en_part = re.sub(r",?\s*CAS:\d[\d/-]*", "", right).strip()
        en_part = CAS_PATTERN.sub("", en_part).strip()  # 移除独立 CAS 号（如 527-07-1）
        # 英文别名分隔符： /
        en_names = [n.strip() for n in re.split(r"\s*/\s*", en_part) if n.strip()]

        mappings.append({
            "cn_names": cn_names,
            "en_names": en_names,
            "cas_numbers": all_cas,
            "raw": raw,
        })
    return mappings


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Written: {path}")


if __name__ == "__main__":
    # 外观颜色
    color_mappings = parse_appearance_colors()
    write_json(ROOT / "appearance_color_mapping.json", {
        "version": "2026.06",
        "description": "产品外观颜色中英文对照表",
        "mappings": color_mappings,
    })
    print(f"  → {len(color_mappings)} appearance color mappings")

    # 报关成分
    ingredient_mappings = parse_ingredients()
    write_json(ROOT / "ingredient_mapping.json", {
        "version": "2026.06",
        "description": "报关成分（化学品）中英文对照表，含CAS号",
        "mappings": ingredient_mappings,
    })
    print(f"  → {len(ingredient_mappings)} ingredient mappings")
