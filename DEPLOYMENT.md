# ShippingHelper 部署与维护文档

## 一、项目概述

ShippingHelper 是一款外贸船务效率工具，基于 Vue 3 + FastAPI + SQLite + OnlyOffice 架构。

**技术栈：**
- 前端：Vue 3 + Vite + Element Plus
- 后端：FastAPI + SQLAlchemy + SQLite
- 文档编辑：OnlyOffice Document Server（Docker）
- 认证：JWT Token

---

## 二、服务器环境

**服务器信息：**
- 系统：Ubuntu 22.04
- 用户：通过 SSH 访问服务器账号，然后切换到 root

**切换到 root：**
```bash
# 方法1：使用 su 切换
su -

# 方法2：使用 sudo（如果当前用户在 sudo 组）
sudo -i

# 方法3：直接执行单条 root 命令
sudo <命令>
```

**验证是否在 root 环境：**
```bash
whoami  # 应该显示 root
python3 --version  # 验证 Python
```

**已安装组件：**
- Python 3.10.12（虚拟环境）
- Node.js 18.x（安装位置：`/opt/node`）
- Nginx
- Docker（OnlyOffice 容器运行在 8080 端口，容器名：`onlyoffice`）
- Tesseract OCR（系统命令：`tesseract`，用于 PDF/图片文字识别）

**额外系统依赖（安装命令）：**
```bash
apt install -y tesseract-ocr
# 如需中文识别：
apt install -y tesseract-ocr-chi-sim
```

**跨平台环境变量：**
以下环境变量可通过 `.env` 文件配置，兼容 Windows 和 Linux：

```env
# Tesseract OCR 路径
TESSERACT_CMD=/usr/bin/tesseract        # Linux
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe  # Windows

# 出口商品编码 Excel 文件路径
EXPORT_CODES_FILE=/path/to/references/2024.12.5 最新出口商品编码及报关成分.xlsx
```

---

## 三、目录结构

```
/path/to/server/shipping-helper/  # 项目根目录（服务器路径）
├── backend/                     # 后端代码
│   ├── app/                    # FastAPI 应用
│   │   ├── api/v1/            # API 路由
│   │   ├── core/              # 核心配置
│   │   ├── models/            # 数据模型
│   │   ├── schemas/           # Pydantic schemas
│   │   └── services/          # 业务服务
│   ├── data/                  # 数据库和用户数据（不纳入 Git）
│   ├── migrations/            # 数据库迁移脚本
│   └── references/            # 文档模板（不纳入 Git）
├── frontend/                   # 前端代码
│   ├── src/                  # Vue 源码
│   └── dist/                 # 构建产物（自动生成）
├── venv/                      # Python 虚拟环境
└── references/                # 文档模板文件（不纳入 Git）
```

---

## 四、服务管理

### 常用命令

```bash
# 查看服务状态
systemctl status shipping-helper

# 重启服务
systemctl restart shipping-helper

# 停止服务
systemctl stop shipping-helper

# 查看日志
journalctl -u shipping-helper -n 50 --no-pager

# 实时查看日志
journalctl -u shipping-helper -f
```

---

## 五、配置说明

### 环境变量
文件位置：`/path/to/server/shipping-helper/backend/.env`

```env
ONLYOFFICE_SECRET_KEY=your-secret-key-here
DOCUMENT_SERVER_URL=http://你的服务器IP/documentserver
API_BASE_URL=http://你的服务器IP:8000
ONLYOFFICE_CALLBACK_BASE_URL=http://你的服务器IP:8000
```

**注意事项：**
- `ONLYOFFICE_SECRET_KEY` 必须与 OnlyOffice Docker 容器的 JWT secret 一致
- `DOCUMENT_SERVER_URL` 是浏览器访问 OnlyOffice 的地址（通过 Nginx 代理）
- 修改后需要 `systemctl restart shipping-helper`

### OnlyOffice JWT 配置
OnlyOffice JWT secret 在 Docker 容器内：
```bash
docker exec onlyoffice cat /etc/onlyoffice/documentserver/local.json | grep -A2 '"secret"'
```

---

## 六、代码更新流程

### 方式1：Git 推送（推荐）

**第一次设置 Git（只需执行一次）：**

```bash
# 本地项目根目录执行
cd /path/to/local/project
git init
git add .
git commit -m "Initial commit"

# 服务器创建 bare 仓库
ssh user@你的服务器 'mkdir -p /path/to/server/shipping-helper.git && cd /path/to/server/shipping-helper.git && git init --bare'

# 本地添加 remote 并推送
git remote add origin user@你的服务器:/path/to/server/shipping-helper.git
git push -u origin main

# 服务器 checkout 到工作目录
ssh user@你的服务器 'cd /path/to/server/shipping-helper && git clone /path/to/server/shipping-helper.git .'
```

**日常更新代码（一键脚本）：**

```bash
# 本地修改代码后，在项目根目录执行：
git add .
git commit -m "描述本次修改"
git push

# 服务器自动拉取并重新构建（需要根据实际路径修改）
ssh user@你的服务器 'cd /path/to/server/shipping-helper && git pull && cd frontend && /opt/node/bin/npm run build && systemctl restart shipping-helper'
```

### 方式2：手动打包上传

```bash
# 1. 本地打包（排除 node_modules 和 .git）
cd /path/to/local
tar --exclude='shippiing_helper/frontend/node_modules' \
    --exclude='shippiing_helper/.git' \
    -czvf shipping-helper.tar.gz shippiing_helper/

# 2. 上传到服务器
scp shipping-helper.tar.gz user@你的服务器:/tmp/

# 3. 服务器解压覆盖
ssh user@你的服务器 'cd /path/to/server/shipping-helper && tar -xzvf /tmp/shipping-helper.tar.gz --strip-components=1'

# 4. 重新构建前端
ssh user@你的服务器 'cd /path/to/server/shipping-helper/frontend && /opt/node/bin/npm run build'

# 5. 重启服务
ssh user@你的服务器 'systemctl restart shipping-helper'
```

---

## 七、数据管理

### 不纳入 Git 的内容
以下文件和目录不会被 Git 管理，不会有冲突：

| 路径 | 说明 |
|------|------|
| `backend/data/` | 数据库文件 `shipping_helper.db`、用户数据 `users.json` |
| `references/` | 文档模板文件（二进制 .xlsx/.docx） |
| `frontend/dist/` | 前端构建产物 |
| `frontend/node_modules/` | npm 依赖 |
| `.env` | 环境变量（包含密钥） |

### 备份数据库
```bash
ssh user@你的服务器 'cp /path/to/server/shipping-helper/backend/data/shipping_helper.db /tmp/shipping_helper_$(date +%Y%m%d).db'
```

---

## 八、端口与访问

| 端口 | 服务 | 说明 |
|------|------|------|
| 80 | Nginx | Web 访问入口 |
| 8000 | FastAPI | 后端 API |
| 8080 | OnlyOffice | 文档编辑服务（Docker） |

**访问地址：**
- 局域网：`http://你的服务器IP`
- OnlyOffice 代理：`http://你的服务器IP/documentserver`

**防火墙开放端口：**
```bash
ufw allow 80/tcp
ufw allow 8000/tcp
ufw allow 8080/tcp
ufw reload
```

---

### 初始 GitHub 同步设置

**从 GitHub clone 到服务器（首次设置）：**

```bash
# 创建项目目录
sudo mkdir -p /path/to/server/shipping-helper
cd /path/to/server/shipping-helper

# 初始化 git（如果目录非空）
sudo git init
sudo git remote add origin https://github.com/你的用户名/你的仓库名.git
sudo git config --global --add safe.directory /path/to/server/shipping-helper
sudo git pull origin main

# 备份并恢复 data 和 references（如果已有）
sudo cp -r /tmp/data_backup /path/to/server/shipping-helper/data
sudo cp -r /tmp/references_backup /path/to/server/shipping-helper/references
sudo chown -R www-data:www-data /path/to/server/shipping-helper/data /path/to/server/shipping-helper/references
```

**日常代码更新（从 GitHub 拉取）：**
```bash
cd /path/to/server/shipping-helper
sudo git pull origin main
sudo systemctl restart shipping-helper
```

---

## 九、用户账号

服务器上用户数据文件：`/path/to/server/shipping-helper/backend/data/users.json`

```json
[
  {"name": "张三", "password": "zhangsan123", "role": "admin"},
  {"name": "肖聪", "password": "123456", "role": "admin"},
  {"name": "万凤", "password": "123456", "role": "admin"}
]
```

添加/修改用户需要编辑此文件后重启服务。

---

## 十、故障排查

### 1. 服务无法启动
```bash
systemctl status shipping-helper
journalctl -u shipping-helper -n 30 --no-pager
```

### 2. OnlyOffice 连接失败
```bash
# 检查 OnlyOffice 容器
docker ps

# 检查 OnlyOffice 是否正常
curl -I http://127.0.0.1:8080

# 检查 JWT secret 是否匹配
grep ONLYOFFICE_SECRET_KEY /path/to/server/shipping-helper/backend/.env
docker exec onlyoffice cat /etc/onlyoffice/documentserver/local.json | grep -A2 '"secret"'
```

### 3. 401 Unauthorized
- 检查 `.env` 配置是否正确
- 重启服务：`systemctl restart shipping-helper`
- 浏览器强制刷新：Ctrl+F5

### 4. 数据库只读
```bash
chown -R www-data:www-data /path/to/server/shipping-helper/backend/data
chmod -R u+w /path/to/server/shipping-helper/backend/data
```

### 5. 前端 500 错误
```bash
journalctl -u shipping-helper -n 50 --no-pager
```

### 6. venv 被删除后重建
如果虚拟环境损坏或丢失：
```bash
# 重新创建 venv
sudo python3 -m venv /path/to/server/shipping-helper/venv

# 安装依赖
sudo /path/to/server/shipping-helper/venv/bin/pip install --upgrade pip
sudo /path/to/server/shipping-helper/venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r /path/to/server/shipping-helper/backend/requirements.txt

# 重启服务
sudo systemctl restart shipping-helper
```

### 7. GitHub 拉取代码（服务器已配置 Git）
```bash
cd /path/to/server/shipping-helper
git pull origin main
sudo systemctl restart shipping-helper
```

### 8. .env 文件损坏或丢失
如果 .env 文件丢失或损坏，需要重新创建：
```bash
# 删除并重建
sudo rm /path/to/server/shipping-helper/backend/.env
sudo touch /path/to/server/shipping-helper/backend/.env
sudo chmod 666 /path/to/server/shipping-helper/backend/.env

# 逐行写入（注意每行单独 echo）
echo "ONLYOFFICE_SECRET_KEY=your-secret-key-here" | sudo tee -a /path/to/server/shipping-helper/backend/.env
echo "DOCUMENT_SERVER_URL=http://你的服务器IP/documentserver" | sudo tee -a /path/to/server/shipping-helper/backend/.env
echo "API_BASE_URL=http://你的服务器IP:8000" | sudo tee -a /path/to/server/shipping-helper/backend/.env
echo "ONLYOFFICE_CALLBACK_BASE_URL=http://你的服务器IP:8000" | sudo tee -a /path/to/server/shipping-helper/backend/.env
echo "TESSERACT_CMD=/usr/bin/tesseract" | sudo tee -a /path/to/server/shipping-helper/backend/.env

# 验证
cat /path/to/server/shipping-helper/backend/.env

# 重启服务
sudo systemctl restart shipping-helper
```

---

## 十一、OnlyOffice 维护

### 重启 OnlyOffice
```bash
docker restart onlyoffice
# 等待 30 秒让服务完全启动
sleep 30
```

### 检查 OnlyOffice 状态
```bash
docker ps
curl -I http://127.0.0.1:8080
```

### 更新 OnlyOffice JWT Secret
如果需要修改 JWT secret：
1. 修改 `backend/.env` 中的 `ONLYOFFICE_SECRET_KEY`
2. 修改 Docker 容器配置：
   ```bash
   docker exec onlyoffice bash -c 'cat > /etc/onlyoffice/documentserver/local.json << EOF
   {
     "services": {
       "CoAuthoring": {
         "token": {
           "enable": {
             "request": {
               "inbox": true,
               "outbox": true
             },
             "browser": true
           },
           "inbox": {
             "header": "Authorization",
             "inBody": false
           },
           "outbox": {
             "header": "Authorization",
             "inBody": false
           }
         },
         "secret": {
           "browser": {
             "string": "your-secret-key-here"
           },
           "inbox": {
             "string": "your-secret-key-here"
           },
           "outbox": {
             "string": "your-secret-key-here"
           },
           "session": {
             "string": "your-secret-key-here"
           }
         }
       }
     }
   }
   EOF'
   ```
3. 重启 OnlyOffice：`docker restart onlyoffice`
4. 重启后端：`systemctl restart shipping-helper`

---

## 十二、配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| systemd 服务 | `/etc/systemd/system/shipping-helper.service` | 后端服务配置 |
| Nginx 配置 | `/etc/nginx/sites-available/shipping-helper` | 网站代理配置 |
| 环境变量 | `/path/to/server/shipping-helper/backend/.env` | 后端配置 |
| 项目代码 | `/path/to/server/shipping-helper/` | 代码根目录 |

### systemd 服务文件内容
```ini
[Unit]
Description=ShippingHelper FastAPI Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/server/shipping-helper/backend
EnvironmentFile=/path/to/server/shipping-helper/backend/.env
Environment="PATH=/path/to/server/shipping-helper/venv/bin"
ExecStart=/path/to/server/shipping-helper/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### Nginx 配置文件内容
```nginx
server {
    listen 80;
    server_name 你的服务器IP;
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /documentserver/ {
        proxy_pass http://127.0.0.1:8080/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /cache/ {
        proxy_pass http://127.0.0.1:8080/cache/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```
