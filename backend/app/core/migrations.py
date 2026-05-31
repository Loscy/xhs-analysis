from sqlalchemy import text

from app.core.database import engine


def run_lightweight_migrations() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS xhs_products (
          id INT AUTO_INCREMENT PRIMARY KEY,
          item_id VARCHAR(64) NOT NULL UNIQUE,
          source_input TEXT NULL,
          source_url TEXT NULL,
          type VARCHAR(16) NOT NULL DEFAULT 'manual',
          title VARCHAR(200) NULL,
          sales_volume VARCHAR(80) NULL,
          shop_id VARCHAR(80) NULL,
          shop_name VARCHAR(120) NULL,
          shop_url TEXT NULL,
          shop_location VARCHAR(120) NULL,
          web_status VARCHAR(16) NOT NULL DEFAULT 'pending',
          web_error TEXT NULL,
          web_data JSON NULL,
          include_detail BOOL NOT NULL DEFAULT FALSE,
          detail_status VARCHAR(16) NOT NULL DEFAULT 'none',
          status VARCHAR(16) NOT NULL DEFAULT 'active',
          collected_at DATETIME NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          INDEX idx_xhs_products_item_id (item_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS xhs_product_skus (
          id INT AUTO_INCREMENT PRIMARY KEY,
          product_id INT NOT NULL,
          sku_id VARCHAR(64) NOT NULL,
          name VARCHAR(255) NULL,
          attrs JSON NULL,
          original_price VARCHAR(40) NULL,
          deal_price VARCHAR(40) NULL,
          image TEXT NULL,
          stock_status VARCHAR(40) NULL,
          device_collected BOOL NOT NULL DEFAULT FALSE,
          raw_data JSON NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          UNIQUE KEY uq_xhs_product_skus_sku_id (sku_id),
          INDEX idx_xhs_product_skus_product_id (product_id),
          CONSTRAINT fk_xhs_product_skus_product_id FOREIGN KEY (product_id) REFERENCES xhs_products(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        "ALTER TABLE xhs_product_skus DROP INDEX uq_xhs_product_skus_product_sku",
        """
        DELETE old_sku FROM xhs_product_skus old_sku
        INNER JOIN xhs_product_skus newer_sku
          ON old_sku.sku_id = newer_sku.sku_id
         AND old_sku.id < newer_sku.id
        """,
        "ALTER TABLE xhs_product_skus ADD UNIQUE KEY uq_xhs_product_skus_sku_id (sku_id)",
        "ALTER TABLE xhs_product_skus ADD COLUMN device_collected BOOL NOT NULL DEFAULT FALSE",
        "ALTER TABLE xhs_tag_queries ADD COLUMN source_input TEXT NULL",
        "ALTER TABLE xhs_tag_queries ADD COLUMN source_url TEXT NULL",
        "ALTER TABLE xhs_tag_queries ADD COLUMN product_id INT NULL",
        "ALTER TABLE xhs_tag_queries ADD COLUMN started_at DATETIME NULL",
        "ALTER TABLE xhs_tag_queries ADD COLUMN finished_at DATETIME NULL",
        "ALTER TABLE xhs_api_keys ADD COLUMN can_view_devices BOOL NOT NULL DEFAULT FALSE",
        "ALTER TABLE xhs_api_keys ADD COLUMN can_manage_keys BOOL NOT NULL DEFAULT FALSE",
        "ALTER TABLE xhs_products ADD COLUMN sales_volume VARCHAR(80) NULL",
        "ALTER TABLE xhs_products ADD COLUMN shop_id VARCHAR(80) NULL",
        "ALTER TABLE xhs_products ADD COLUMN shop_name VARCHAR(120) NULL",
        "ALTER TABLE xhs_products ADD COLUMN shop_url TEXT NULL",
        "ALTER TABLE xhs_products ADD COLUMN shop_location VARCHAR(120) NULL",
        "ALTER TABLE xhs_products ADD COLUMN web_status VARCHAR(16) NOT NULL DEFAULT 'pending'",
        "ALTER TABLE xhs_products ADD COLUMN web_error TEXT NULL",
        "ALTER TABLE xhs_products ADD COLUMN web_data JSON NULL",
        "ALTER TABLE xhs_products ADD COLUMN include_detail BOOL NOT NULL DEFAULT FALSE",
        "ALTER TABLE xhs_products ADD COLUMN detail_status VARCHAR(16) NOT NULL DEFAULT 'none'",
        "ALTER TABLE xhs_products ADD COLUMN collected_at DATETIME NULL",
        "ALTER TABLE xhs_products ADD COLUMN is_main BOOL NOT NULL DEFAULT TRUE",
        "ALTER TABLE xhs_products ADD COLUMN parent_product_id INT NULL",
        "ALTER TABLE xhs_products ADD COLUMN device_collected BOOL NOT NULL DEFAULT FALSE",
        "ALTER TABLE xhs_products ADD COLUMN original_price VARCHAR(40) NULL",
        "ALTER TABLE xhs_products ADD COLUMN deal_price VARCHAR(40) NULL",
        """
        CREATE TABLE IF NOT EXISTS xhs_product_groups (
          id INT AUTO_INCREMENT PRIMARY KEY,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        "ALTER TABLE xhs_products ADD COLUMN group_id INT NULL",
        "CREATE INDEX idx_xhs_products_group_id ON xhs_products (group_id)",
        """
        CREATE TABLE IF NOT EXISTS xhs_tag_metrics (
          id INT AUTO_INCREMENT PRIMARY KEY,
          sku_id VARCHAR(64) NOT NULL,
          product_id INT NOT NULL,
          dim_key VARCHAR(32) NOT NULL,
          dim_value INT NOT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_tag_metrics_sku_dim (sku_id, dim_key),
          INDEX idx_tag_metrics_product_id (product_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
    ]
    with engine.begin() as conn:
        for statement in statements:
            try:
                conn.execute(text(statement))
            except Exception as e:
                message = str(e).lower()
                if (
                    "duplicate column" in message
                    or "already exists" in message
                    or "doesn't exist" in message
                    or "can't drop" in message
                    or "duplicate key name" in message
                ):
                    continue
                raise
        admins = conn.execute(text("SELECT id FROM xhs_api_keys WHERE name = 'admin' ORDER BY created_at DESC, id DESC")).fetchall()
        if admins:
            primary_admin_id = admins[0][0]
            conn.execute(
                text(
                    "UPDATE xhs_api_keys SET can_view_devices = TRUE, can_manage_keys = TRUE, status = 'active' "
                    "WHERE id = :id"
                ),
                {"id": primary_admin_id},
            )
            for row in admins[1:]:
                conn.execute(
                    text(
                        "UPDATE xhs_api_keys SET name = CONCAT('admin-duplicate-', id), "
                        "can_view_devices = FALSE, can_manage_keys = FALSE "
                        "WHERE id = :id"
                    ),
                    {"id": row[0]},
                )
        _migrate_to_group_id(conn)
        _backfill_tag_metrics(conn)


def _migrate_to_group_id(conn) -> None:
    has_parent = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'xhs_products' AND COLUMN_NAME = 'parent_product_id'"
    )).scalar()
    if not has_parent:
        return
    products_with_parent = conn.execute(text(
        "SELECT id, parent_product_id FROM xhs_products WHERE parent_product_id IS NOT NULL AND group_id IS NULL"
    )).fetchall()
    if not products_with_parent:
        return
    parent_ids = {row[1] for row in products_with_parent}
    for pid in parent_ids:
        group_result = conn.execute(text("INSERT INTO xhs_product_groups () VALUES ()"))
        conn.execute(text("UPDATE xhs_products SET group_id = :gid WHERE id = :pid"), {"gid": group_result.lastrowid, "pid": pid})
        conn.execute(text("UPDATE xhs_products SET group_id = :gid WHERE parent_product_id = :pid AND group_id IS NULL"), {"gid": group_result.lastrowid, "pid": pid})
    conn.execute(text("UPDATE xhs_products SET group_id = NULL WHERE group_id IS NULL AND parent_product_id IS NULL AND is_main = TRUE"))
    try:
        conn.execute(text("ALTER TABLE xhs_products DROP COLUMN parent_product_id"))
    except Exception:
        pass


def _backfill_tag_metrics(conn) -> None:
    import json
    import re
    DIMENSION_PATTERNS = [
        ("24h_cart", re.compile(r"24小时内(\d+)\+?人加购")),
        ("7d_fav", re.compile(r"近7天新增(\d+)\+?人收藏")),
    ]
    existing = conn.execute(text("SELECT DISTINCT sku_id, dim_key, DATE(created_at) FROM xhs_tag_metrics")).fetchall()
    seen = {(r[0], r[1], str(r[2])) for r in existing}
    rows = conn.execute(
        text(
            "SELECT q.sku_id, q.product_id, q.tags, q.created_at "
            "FROM xhs_tag_queries q "
            "WHERE q.status = 'success' AND q.tags IS NOT NULL AND JSON_LENGTH(q.tags) > 0"
        )
    ).fetchall()
    for sku_id, product_id, tags_json, created_at in rows:
        if not tags_json:
            continue
        tags = json.loads(tags_json) if isinstance(tags_json, str) else tags_json
        for dim_key, pattern in DIMENSION_PATTERNS:
            for tag in tags:
                m = pattern.search(str(tag))
                if m:
                    day_key = (sku_id, dim_key, str(created_at.date()))
                    if day_key not in seen:
                        conn.execute(
                            text(
                                "INSERT INTO xhs_tag_metrics (sku_id, product_id, dim_key, dim_value, created_at) "
                                "VALUES (:sku_id, :product_id, :dim_key, :dim_value, :created_at)"
                            ),
                            {"sku_id": sku_id, "product_id": product_id or 0, "dim_key": dim_key, "dim_value": int(m.group(1)), "created_at": created_at},
                        )
                        seen.add(day_key)
