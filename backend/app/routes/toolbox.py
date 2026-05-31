from pathlib import Path

from flask import Blueprint, request

from ..extensions import db
from ..models import ToolboxItem
from ..security import current_user, is_admin, is_teacher, login_required
from ..utils import APIError, audit, get_json, ok, paginate, save_upload, update_model
from .files import _safe_send

bp = Blueprint("toolbox", __name__)


@bp.get("")
@login_required()
def list_tools():
    query = ToolboxItem.query.filter_by(is_deleted=False)
    if request.args.get("include_disabled") != "1":
        query = query.filter_by(is_enabled=True)
    return ok(paginate(query.order_by(ToolboxItem.updated_at.desc())))


@bp.post("")
@login_required()
def upload_tool():
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    file = request.files.get("file")
    if not file:
        raise APIError("NO_FILE", "File is required.", 422)
    meta = save_upload(file, "toolbox", None)
    tool = ToolboxItem(
        name=request.form.get("name") or Path(file.filename or "tool").stem,
        description=request.form.get("description", ""),
        version=request.form.get("version", "1.0.0"),
        file_path=meta["file_path"],
        file_size=meta["file_size"],
        uploader_id=actor.id,
    )
    db.session.add(tool)
    db.session.flush()
    audit("upload_toolbox_item", tool, after=tool.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(tool.to_dict(), status=201)


@bp.patch("/<int:tool_id>")
@login_required()
def update_tool(tool_id):
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    tool = ToolboxItem.query.get_or_404(tool_id)
    before = tool.to_dict()
    update_model(tool, get_json(), ["name", "description", "version", "is_enabled"])
    db.session.add(tool)
    audit("update_toolbox_item", tool, before=before, after=tool.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(tool.to_dict())


@bp.post("/<int:tool_id>/disable")
@login_required()
def disable_tool(tool_id):
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    tool = ToolboxItem.query.get_or_404(tool_id)
    before = tool.to_dict()
    tool.is_enabled = False
    db.session.add(tool)
    audit("disable_toolbox_item", tool, before=before, after=tool.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(tool.to_dict())


@bp.delete("/<int:tool_id>")
@login_required()
def delete_tool(tool_id):
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    tool = ToolboxItem.query.get_or_404(tool_id)
    before = tool.to_dict()
    tool.soft_delete(actor.id, get_json().get("reason"))
    db.session.add(tool)
    audit("delete_toolbox_item", tool, before=before, after=tool.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(tool.to_dict())


@bp.get("/<int:tool_id>/download")
@login_required()
def download_tool(tool_id):
    tool = ToolboxItem.query.get_or_404(tool_id)
    if tool.is_deleted or not tool.is_enabled:
        raise APIError("NOT_FOUND", "Resource not found.", 404)
    return _safe_send(tool.file_path, Path(tool.file_path).name)
