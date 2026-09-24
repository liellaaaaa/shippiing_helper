"""校准 packaging_types / pallets — 船务《产品包装资料(2026.9.23)》

卡板 CBM 按外形：1.0*1.0*0.15=0.15，1.1*1.1*0.15=0.1815
卡板皮重：16 / 19（船务确认）
"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "shipping_helper.db")

# name, dims, cbm, tare_kg, gross_kg, net_kg, barrel_type, is_palletizable, no_pallet_qty, pallet_qty_1x1, pallet_qty_1_1x1_1
PACKAGES = [
    ("30kg蓝桶", "250*250*430mm", 0.026, 2.0, 32.0, 30.0, "胶桶", 1, None, None, 24),
    ("25kg/包", "200*500*800mm", 0.028, 0.5, 25.5, 25.0, "胶桶", 1, None, None, 40),
    ("25kg 正方罐（蓝色）", "270*270*410mm", 0.03, 2.0, 27.0, 25.0, "胶桶", 1, None, None, 20),
    ("25kg 纸桶", "310*310*400mm", 0.039, 2.0, 27.0, 25.0, "纸桶", 1, None, None, 18),
    ("50kg蓝桶(细口)", "395*395*585mm", 0.09, 2.5, 52.5, 50.0, "胶桶", 1, None, None, 18),
    ("50kg蓝桶(大口)", "330*390*590mm", 0.08, 2.5, 52.5, 50.0, "胶桶", 1, None, None, 18),
    ("50kg纸桶", "410*410*高500mm", 0.085, 2.5, 52.5, 50.0, "纸桶", 1, None, None, 12),
    ("60kg蓝桶", "320*410*640mm", 0.09, 3.5, 63.5, 60.0, "胶桶", 1, None, None, 16),
    ("125kg新款胶桶", "510*510*810mm", 0.21, 6.0, 131.0, 125.0, "胶桶", 1, 116, 4, 5),
    ("150kg新款胶桶", "450*450*970mm", 0.196, 9.0, 159.0, 150.0, "胶桶", 1, None, None, 4),
    ("200kg双环闭口桶", "590*590*930mm", 0.31, 10.0, 210.0, 200.0, "胶桶", 1, 80, None, 2),
    ("1吨桶", "1200*1000*1150mm", 1.38, 58.0, 1058.0, 1000.0, "IBC", 0, 20, None, 1),
]

PALLETS = [
    ("1.0*1.0m", "1000*1000mm (H150mm)", 16.0, 0.15),
    ("1.1*1.1m", "1100*1100mm (H150mm)", 19.0, 0.1815),
]


def upgrade():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for name, dims, weight, cbm in PALLETS:
        cur.execute(
            """
            INSERT INTO pallets (name, dims, weight_kg, cbm) VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET dims=excluded.dims, weight_kg=excluded.weight_kg, cbm=excluded.cbm
            """,
            (name, dims, weight, cbm),
        )
    # 兼容旧名（若有 1.0*1.0 / 1.1*1.1 变体则删除重复）
    cur.execute("DELETE FROM pallets WHERE name NOT IN ('1.0*1.0m', '1.1*1.1m')")

    # 清掉旧包装（含错误命名），按名单重建
    cur.execute("DELETE FROM packaging_types")
    for row in PACKAGES:
        cur.execute(
            """
            INSERT INTO packaging_types
            (name, dims, cbm, tare_kg, gross_kg, net_kg, barrel_type, is_palletizable,
             no_pallet_qty, pallet_qty_1x1, pallet_qty_1_1x1_1)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )

    conn.commit()
    conn.close()
    print("Migration 021: packaging_types + pallets calibrated")


def downgrade():
    print("Migration 021: no-op downgrade (keep calibrated specs)")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
