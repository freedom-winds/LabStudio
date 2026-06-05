# Lexy Lab 实验室垂直管理平台

[English README](README.md)

前后端分离实现：

- 后端：Flask + Flask-SQLAlchemy + SQLite，使用 ORM 管理业务模型，本地文件系统保存上传文件。
- 前端：Vue 3 + Vite + Vue Router + lucide 图标。
- UI：按 `ui_design/` 设计稿实现左侧导航、顶部状态栏、白色卡片、蓝色主操作与实验详情二级导航。

## Usage

当前项目已落地于 20+ 所学校，服务 300+ 名用户。

## 目录

```text
backend/   Flask REST API、ORM 模型、权限、种子数据、测试
frontend/  Vue SPA、页面、组件、设计系统样式
ui_design/ 需求提供的 UI 设计稿
```

## 启动

后端：

```powershell
cd backend
python -m flask --app app init-db
python run.py
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

访问：`http://localhost:5173`

后端默认端口：`http://127.0.0.1:5055`

## 初始账号

初始化后仅创建系统管理员账号：

```text
系统管理员：00000000 / Admin1234!
```

其他教师、学生、年度管理员等账号需要由管理员在用户管理中创建。新建账号默认密码等于用户名，首次登录后可在系统内改密。

## 验证

```powershell
python -m pytest backend -q
cd frontend
npm run build
```

部署步骤见 [deploy.md](deploy.md)。
