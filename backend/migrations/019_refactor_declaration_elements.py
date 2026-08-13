"""迁移脚本：重构申报要素台账

1. 创建新表：hs_code_fields, declaration_products, declaration_values
2. 从 hs_codes.json 导入字段定义和产品数据
3. 从旧 declaration_elements 表迁移补充数据
"""

import json
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "shipping_helper.db")
HS_CODES_JSON = os.path.join(os.path.dirname(__file__), "..", "..", "hs_codes.json")


def _table_exists(cursor, table_name: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = [row[1] for row in cursor.fetchall()]
    return column_name in cols


def create_tables(conn):
    """创建新表"""
    cursor = conn.cursor()

    # 创建 hs_code_fields 表
    if not _table_exists(cursor, "hs_code_fields"):
        cursor.execute("""
            CREATE TABLE hs_code_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hs_code TEXT NOT NULL,
                field_name TEXT NOT NULL,
                field_type TEXT DEFAULT 'text',
                sort_order INTEGER DEFAULT 0,
                is_required INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(hs_code, field_name)
            )
        """)
        cursor.execute("CREATE INDEX idx_hs_code_fields_hs_code ON hs_code_fields(hs_code)")
        print("Created table: hs_code_fields")

    # 创建 declaration_products 表
    if not _table_exists(cursor, "declaration_products"):
        cursor.execute("""
            CREATE TABLE declaration_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hs_code TEXT NOT NULL,
                product_name TEXT NOT NULL,
                website_name TEXT,
                product_description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(hs_code, product_name)
            )
        """)
        cursor.execute("CREATE INDEX idx_declaration_products_hs_code ON declaration_products(hs_code)")
        print("Created table: declaration_products")

    # 创建 declaration_values 表
    if not _table_exists(cursor, "declaration_values"):
        cursor.execute("""
            CREATE TABLE declaration_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                field_name TEXT NOT NULL,
                field_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES declaration_products(id) ON DELETE CASCADE,
                UNIQUE(product_id, field_name)
            )
        """)
        cursor.execute("CREATE INDEX idx_declaration_values_product_id ON declaration_values(product_id)")
        print("Created table: declaration_values")

    conn.commit()


def seed_hs_code_fields(conn):
    """从 hs_codes.json 导入数据"""
    if not os.path.exists(HS_CODES_JSON):
        print(f"Warning: {HS_CODES_JSON} not found, skipping seed")
        return

    with open(HS_CODES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    for hs_code, info in data.items():
        fields = info.get("申报要素字段", [])
        products = info.get("数据库中商品名称及要素值", [])
        website_name = info.get("网站商品名称", "")
        product_description = info.get("商品描述", "")

        # 插入字段定义
        for idx, field_name in enumerate(fields):
            cursor.execute("""
                INSERT OR IGNORE INTO hs_code_fields (hs_code, field_name, field_type, sort_order, is_required, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (hs_code, field_name, "text", idx, 0, now))

        # 插入产品和要素值
        for product in products:
            product_name = product.get("商品名称", "")
            if not product_name:
                continue

            # 插入产品
            cursor.execute("""
                INSERT OR IGNORE INTO declaration_products (hs_code, product_name, website_name, product_description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (hs_code, product_name, website_name, product_description, now, now))

            # 获取产品 ID
            cursor.execute("SELECT id FROM declaration_products WHERE hs_code = ? AND product_name = ?", 
                         (hs_code, product_name))
            row = cursor.fetchone()
            if not row:
                continue
            product_id = row[0]

            # 插入要素值
            for field_name in fields:
                field_value = product.get(field_name, "")
                if field_value:  # 只插入非空值
                    cursor.execute("""
                        INSERT OR IGNORE INTO declaration_values (product_id, field_name, field_value, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (product_id, field_name, field_value, now, now))

    conn.commit()
    print(f"Seeded data from {HS_CODES_JSON}")


def migrate_from_old_table(conn):
    """从旧 declaration_elements 表迁移数据"""
    cursor = conn.cursor()

    # 检查旧表是否存在
    if not _table_exists(cursor, "declaration_elements"):
        print("Old table declaration_elements not found, skipping migration")
        return

    now = datetime.utcnow().isoformat()

    # 查询旧表数据
    cursor.execute("SELECT hs_code, declaration_name, elements_text FROM declaration_elements")
    old_records = cursor.fetchall()

    migrated_count = 0
    for hs_code, declaration_name, elements_text in old_records:
        # 检查产品是否已存在
        cursor.execute("SELECT id FROM declaration_products WHERE hs_code = ? AND product_name = ?",
                     (hs_code, declaration_name))
        row = cursor.fetchone()

        if row:
            # 产品已存在，跳过
            continue

        # 创建新产品
        cursor.execute("""
            INSERT INTO declaration_products (hs_code, product_name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (hs_code, declaration_name, now, now))
        product_id = cursor.lastrowid

        # 解析 elements_text 并插入值
        if elements_text:
            pairs = elements_text.split("|")
            for pair in pairs:
                if "：" in pair:
                    key, value = pair.split("：", 1)
                    if key and value:
                        cursor.execute("""
                            INSERT OR IGNORE INTO declaration_values (product_id, field_name, field_value, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (product_id, key.strip(), value.strip(), now, now))

        migrated_count += 1

    conn.commit()
    print(f"Migrated {migrated_count} records from old table")


def upgrade():
    """执行迁移"""
    conn = sqlite3.connect(DB_PATH)
    try:
        print("Starting declaration elements refactoring migration...")
        create_tables(conn)
        seed_hs_code_fields(conn)
        migrate_from_old_table(conn)
        print("Migration completed successfully")
    finally:
        conn.close()


def downgrade():
    """回滚迁移（删除新表）"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS declaration_values")
        cursor.execute("DROP TABLE IF EXISTS declaration_products")
        cursor.execute("DROP TABLE IF EXISTS hs_code_fields")
        conn.commit()
        print("Downgrade completed: dropped new tables")
    finally:
        conn.close()


if __name__ == "__main__":
    upgrade()
