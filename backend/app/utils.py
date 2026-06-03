from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from flask import current_app, jsonify, request
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .extensions import db
from .models import AuditLog, FileAsset, StepFile, now_iso


class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def ok(data: Any = None, status: int = 200, **meta: Any):
    payload = {"data": data}
    payload.update(meta)
    return jsonify(payload), status


def fail(code: str, message: str, status: int):
    return jsonify({"code": code, "message": message}), status


def get_json() -> dict:
    if not request.is_json:
        return {}
    return request.get_json(silent=True) or {}


def require_fields(data: dict, fields: list[str]) -> None:
    missing = [field for field in fields if data.get(field) in (None, "")]
    if missing:
        raise APIError("VALIDATION_ERROR", f"Missing required fields: {', '.join(missing)}", 422)


def validate_username(username: str) -> None:
    if not re.fullmatch(r"\d{8}", username or ""):
        raise APIError("INVALID_USERNAME", "Username must be 8 digits.", 422)


def validate_password(password: str) -> None:
    if not 8 <= len(password or "") <= 16:
        raise APIError("INVALID_PASSWORD", "Password length must be 8 to 16 characters.", 422)
    categories = 0
    categories += bool(re.search(r"[A-Za-z]", password))
    categories += bool(re.search(r"\d", password))
    categories += bool(re.search(r"[^A-Za-z0-9]", password))
    if categories < 2:
        raise APIError("INVALID_PASSWORD", "Password must contain at least two character types.", 422)


def make_token() -> str:
    return secrets.token_urlsafe(48)


def token_expires_at() -> str:
    days = int(current_app.config.get("TOKEN_EXPIRE_DAYS", 14))
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()


def parse_iso(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def paginate(query, default_per_page: int = 50) -> dict:
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", default_per_page)), 1), 200)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [item.to_dict() for item in items],
        "page": page,
        "per_page": per_page,
        "total": total,
    }


def audit(action: str, obj: Any, before: dict | None = None, after: dict | None = None, actor_id: int | None = None) -> None:
    object_type = obj.__class__.__name__ if obj is not None else "System"
    object_id = getattr(obj, "id", None)
    log = AuditLog(
        actor_id=actor_id,
        action_type=action,
        object_type=object_type,
        object_id=object_id,
        before_data=json.dumps(before, ensure_ascii=False) if before is not None else None,
        after_data=json.dumps(after, ensure_ascii=False) if after is not None else None,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr) if request else None,
        user_agent=request.headers.get("User-Agent", "")[:255] if request else None,
    )
    db.session.add(log)


BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".sh", ".ps1", ".js", ".msi", ".dll", ".com", ".scr"}
DOCUMENT_EXTENSIONS = {".doc", ".docx", ".pdf", ".xls", ".xlsx", ".jpg", ".jpeg", ".png", ".txt", ".zip"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
DATA_EXTENSIONS = {".csv", ".xlsx", ".txt", ".json", ".dat"}
PPT_EXTENSIONS = {".ppt", ".pptx", ".pdf"}
AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def file_category(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in DATA_EXTENSIONS:
        return "data"
    return "document"


def validate_upload(file: FileStorage, category: str | None = None) -> None:
    ext = Path(file.filename or "").suffix.lower()
    if not file.filename or ext in BLOCKED_EXTENSIONS:
        raise APIError("INVALID_FILE", "File type is not allowed.", 422)
    if category == "ppt" and ext not in PPT_EXTENSIONS:
        raise APIError("INVALID_FILE", "Only PPT/PPTX/PDF files are allowed for presentation versions.", 422)
    if category == "avatar":
        if ext not in AVATAR_EXTENSIONS or not (file.mimetype or "").startswith("image/"):
            raise APIError("INVALID_FILE", "Only PNG/JPG/JPEG/WEBP images are allowed for avatars.", 422)


def save_upload(file: FileStorage, owner: str, owner_id: int | None = None, category: str | None = None) -> dict:
    validate_upload(file, category)
    root = Path(current_app.config["UPLOAD_ROOT"])
    folder = root / owner / (str(owner_id) if owner_id is not None else "general")
    folder.mkdir(parents=True, exist_ok=True)
    original = secure_filename(file.filename or "upload.bin")
    ext = Path(original).suffix.lower()
    stored = f"{secrets.token_hex(16)}{ext}"
    path = folder / stored
    file.save(path)
    return {
        "original_filename": file.filename or original,
        "stored_filename": stored,
        "file_path": str(path),
        "file_ext": ext,
        "mime_type": file.mimetype,
        "file_size": path.stat().st_size,
    }


def create_file_asset(file: FileStorage, owner_type: str, owner_id: int | None, uploader_id: int) -> FileAsset:
    meta = save_upload(file, owner_type, owner_id)
    asset = FileAsset(owner_type=owner_type, owner_id=owner_id, uploader_id=uploader_id, **meta)
    db.session.add(asset)
    return asset


def create_step_file(file: FileStorage, step_id: int, uploader_id: int, category: str | None = None) -> StepFile:
    meta = save_upload(file, "steps", step_id)
    category = category or file_category(meta["original_filename"])
    if category == "document" and meta["file_size"] > 20 * 1024 * 1024:
        raise APIError("FILE_TOO_LARGE", "Document files cannot exceed 20MB.", 413)
    if category == "video" and meta["file_size"] > 1024 * 1024 * 1024:
        raise APIError("FILE_TOO_LARGE", "Video files cannot exceed 1GB.", 413)
    step_file = StepFile(step_id=step_id, uploader_id=uploader_id, file_category=category, **meta)
    db.session.add(step_file)
    return step_file


def update_model(model: Any, data: dict, fields: list[str]) -> None:
    for field in fields:
        if field in data:
            setattr(model, field, data[field])


def not_deleted(query):
    return query.filter_by(is_deleted=False)
