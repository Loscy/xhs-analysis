# XHS Analysis

小红书商品页 App 标签采集项目。后端使用 FastAPI，前端使用 React，数据库使用 MySQL。当前采集方式沿用已验证的远程 Android ADB + UIAutomator 方案。

## 功能

- 商品标签查询：`GET /tags?input=分享文案/短链/商品URL/商品ID`
- 全局 `sk-xxx` 密钥校验，支持过期时间
- 密钥管理：创建、列表、停用
- 远程 Android 管理：记录设备、ADB serial、手机 IP、SSH 反向端口、在线状态
- 查询历史：保存 SKU、标签、错误、耗时
- React 控制台：查询、远程安卓、密钥三个页面，适配移动端

## 目录

```text
backend/   FastAPI + SQLAlchemy + MySQL
frontend/  React + Vite
deploy/    systemd / nginx / Ubuntu 安装脚本
```

## 数据库设计

`api_keys`

| 字段 | 说明 |
| --- | --- |
| id | 主键 |
| name | 密钥名称 |
| key_prefix | 前缀展示，例如 `sk-abc...` |
| key_hash | SHA-256，不保存明文 |
| expires_at | 过期时间，可为空 |
| last_used_at | 最近使用时间 |
| status | `active` / `revoked` |
| created_at / updated_at | 时间戳 |

`android_devices`

| 字段 | 说明 |
| --- | --- |
| id | 主键 |
| name | 设备名称 |
| adb_serial | 例如 `127.0.0.1:15555` |
| phone_ip | 手机 Wi-Fi IP |
| ssh_remote_port | 云端反向端口 |
| model | 设备型号 |
| app_package | 默认 `com.xingin.xhs` |
| status | 设备状态 |
| notes | 备注 |
| last_seen_at | 最近成功采集时间 |
| created_at / updated_at | 时间戳 |

`tag_queries`

| 字段 | 说明 |
| --- | --- |
| id | 主键 |
| sku_id | 商品 ID |
| status | `success` / `failed` |
| tags | JSON 标签数组 |
| raw_items | JSON UI 节点信息 |
| error_message | 错误信息 |
| elapsed_ms | 耗时 |
| device_id | 关联设备 |
| api_key_id | 关联密钥 |
| created_at | 创建时间 |

## 后端本地启动

需要 Python 3.9+ 和 MySQL。

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`.env` 示例：

```bash
DATABASE_URL=mysql+pymysql://xhs:xhs_password@127.0.0.1:3306/xhs_analysis
ADB_SERIAL=127.0.0.1:15555
UI_DUMP_DIR=/tmp/xhs-ui-tags
CORS_ORIGINS=*
```

未勾选“包含细节信息”时，系统只调用公开网页接口补全商品名、销量、店铺和 SKU 价格；勾选或点击“补充细节”后才分配在线且闲置的安卓设备采集 App 细节标签。

创建首个 admin key：

```bash
cd backend
source .venv/bin/activate
python -m scripts.create_admin_key admin 2026-12-31T23:59:59
```

## 前端本地启动

```bash
cd frontend
npm install
npm run dev
```

访问：

```text
http://127.0.0.1:5173
```

## API 使用

```bash
curl \
  -H "X-API-Key: sk-xxx" \
  "http://139.224.221.140:18876/tags?input=https%3A%2F%2Fxhslink.com%2Fm%2F314GLxjHAms"
```

也支持：

```bash
Authorization: Bearer sk-xxx
```

支持输入：

```text
69d54072a57e4e0001aec100
https://www.xiaohongshu.com/goods-detail/69d54072a57e4e0001aec100?...
https://xhslink.com/m/314GLxjHAms
【小红书】... https://xhslink.com/m/314GLxjHAms ...
```

## Linux 部署

建议部署到：

```text
/opt/xhs-analysis
```

配置 MySQL：

```sql
CREATE DATABASE xhs_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'xhs'@'%' IDENTIFIED BY 'xhs_password';
GRANT ALL PRIVILEGES ON xhs_analysis.* TO 'xhs'@'%';
FLUSH PRIVILEGES;
```

部署：

```bash
cd /opt/xhs-analysis
cp backend/.env.example backend/.env
vim backend/.env
bash deploy/install_ubuntu.sh
```

创建首个密钥：

```bash
cd /opt/xhs-analysis/backend
. .venv/bin/activate
python -m scripts.create_admin_key admin 2026-12-31T23:59:59
```

服务管理：

```bash
systemctl status xhs-analysis-api --no-pager
systemctl restart xhs-analysis-api
journalctl -u xhs-analysis-api -f
```

## 远程 Android 隧道

手机 Termux：

```bash
termux-wake-lock
autossh -M 0 -N \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -R 15555:192.168.2.83:5555 \
  root@139.224.221.140
```

云服务器：

```bash
adb kill-server
adb start-server
adb disconnect 127.0.0.1:15555
adb connect 127.0.0.1:15555
adb devices -l
```

必须看到：

```text
127.0.0.1:15555 device
```
