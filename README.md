# NandRX Lab Vertical Laboratory Management Platform

[中文说明](README.zh-CN.md)

A decoupled frontend and backend implementation:

- Backend: Flask + Flask-SQLAlchemy + SQLite, using ORM-managed business models and local filesystem storage for uploaded files.
- Frontend: Vue 3 + Vite + Vue Router + lucide icons.
- UI: Implements the `ui_design/` design draft, including the left navigation, top status bar, white cards, blue primary actions, and secondary navigation for experiment details.

## Usage

This project has already been deployed in 20+ schools and serves more than 300 users.

## Directory

```text
backend/   Flask REST API, ORM models, permissions, seed data, tests
frontend/  Vue SPA, pages, components, design system styles
ui_design/ UI design draft provided with the requirements
```

## Getting Started

Backend:

```powershell
cd backend
python -m flask --app app init-db
python run.py
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Visit: `http://localhost:5173`

Default backend port: `http://127.0.0.1:5055`

## Initial Account

After initialization, only the system administrator account is created:

```text
System administrator: 00000000 / Admin1234!
```

Other teacher, student, and annual administrator accounts must be created by an administrator in user management. The default password for a newly created account is the same as the username, and users can change it in the system after first login.

## Verification

```powershell
python -m pytest backend -q
cd frontend
npm run build
```

See [deploy.md](deploy.md) for deployment steps.
