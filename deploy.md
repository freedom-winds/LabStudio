# 部署文档

本文档面向内网或单机服务器部署，推荐后端监听本机 `5055`，前端静态文件由 Nginx 或同类 Web 服务托管，并把 `/api` 反向代理到后端。

## 环境要求

- Python 3.11+
- Node.js 20+
- SQLite 3
- Nginx 或其他静态文件服务

## 后端部署

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\pip install -r requirements.txt
```

生产环境建议至少设置以下环境变量：

```powershell
$env:SECRET_KEY = "替换为高强度随机字符串"
$env:SQLALCHEMY_DATABASE_URI = "sqlite:///F:/projects/LabStudio/backend/data/lexy_lab.db"
$env:UPLOAD_ROOT = "F:/projects/LabStudio/backend/uploads"
$env:TOKEN_EXPIRE_DAYS = "14"
```

首次部署初始化数据库：

```powershell
.\.venv\Scripts\python -m flask --app app init-db
```

注意：`init-db` 会重建数据库，只应在首次部署或明确需要重置数据时执行。初始化后系统仅包含一个管理员账号：

```text
00000000 / Admin1234!
```

启动后端：

```powershell
.\.venv\Scripts\python -m waitress --listen=127.0.0.1:5055 run:app
```

开发或临时演示也可使用：

```powershell
.\.venv\Scripts\python run.py
```

## 前端部署

```powershell
cd frontend
npm install
npm run build
```

构建产物在 `frontend/dist/`。将该目录配置为站点根目录即可。

如果前端和后端同域部署，不需要设置 `VITE_API_BASE`。如果后端使用独立域名或端口，构建前设置：

```powershell
$env:VITE_API_BASE = "https://example.com"
npm run build
```

## Nginx 示例

```nginx
server {
    listen 80;
    server_name lab.example.local;

    root /srv/LabStudio/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:5055/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## 运维检查

后端接口检查：

```powershell
Invoke-WebRequest http://127.0.0.1:5055/api/public/honors
```

前端构建检查：

```powershell
cd frontend
npm run build
```

建议定期备份：

- `backend/data/lexy_lab.db`
- `backend/uploads/`

升级前先停止后端服务，备份数据库和上传目录，再更新代码、安装依赖并重新构建前端。
