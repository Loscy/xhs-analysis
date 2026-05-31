CREATE TABLE IF NOT EXISTS xhs_api_keys (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  key_prefix VARCHAR(16) NOT NULL,
  key_hash VARCHAR(64) NOT NULL UNIQUE,
  expires_at DATETIME NULL,
  last_used_at DATETIME NULL,
  can_view_devices BOOLEAN NOT NULL DEFAULT FALSE,
  can_manage_keys BOOLEAN NOT NULL DEFAULT FALSE,
  status VARCHAR(16) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_xhs_api_keys_key_prefix (key_prefix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS xhs_android_devices (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  adb_serial VARCHAR(80) NOT NULL UNIQUE,
  phone_ip VARCHAR(64) NULL,
  ssh_remote_port INT NULL,
  model VARCHAR(80) NULL,
  app_package VARCHAR(120) NOT NULL DEFAULT 'com.xingin.xhs',
  status VARCHAR(16) NOT NULL DEFAULT 'active',
  notes TEXT NULL,
  last_seen_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS xhs_tag_queries (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sku_id VARCHAR(64) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'success',
  tags JSON NULL,
  raw_items JSON NULL,
  error_message TEXT NULL,
  elapsed_ms INT NULL,
  source_input TEXT NULL,
  source_url TEXT NULL,
  device_id INT NULL,
  api_key_id INT NULL,
  product_id INT NULL,
  started_at DATETIME NULL,
  finished_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_xhs_tag_queries_sku_id (sku_id),
  CONSTRAINT fk_xhs_tag_queries_device_id FOREIGN KEY (device_id) REFERENCES xhs_android_devices(id),
  CONSTRAINT fk_xhs_tag_queries_api_key_id FOREIGN KEY (api_key_id) REFERENCES xhs_api_keys(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS xhs_product_groups (
  id INT AUTO_INCREMENT PRIMARY KEY,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
  include_detail BOOLEAN NOT NULL DEFAULT FALSE,
  detail_status VARCHAR(16) NOT NULL DEFAULT 'none',
  status VARCHAR(16) NOT NULL DEFAULT 'active',
  is_main BOOLEAN NOT NULL DEFAULT TRUE,
  group_id INT NULL,
  collected_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_xhs_products_item_id (item_id),
  INDEX idx_xhs_products_group_id (group_id),
  CONSTRAINT fk_xhs_products_group_id FOREIGN KEY (group_id) REFERENCES xhs_product_groups(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS xhs_tag_metrics (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sku_id VARCHAR(64) NOT NULL,
  product_id INT NOT NULL,
  dim_key VARCHAR(32) NOT NULL,
  dim_value INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_tag_metrics_sku_dim (sku_id, dim_key),
  INDEX idx_tag_metrics_product_id (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
