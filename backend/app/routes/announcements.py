from flask import Blueprint, request

from ..extensions import db
from ..models import Announcement
from ..security import current_user, is_admin, is_teacher, login_required
from ..utils import APIError, audit, get_json, ok, paginate, require_fields, update_model

bp = Blueprint("announcements", __name__)


@bp.get("")
@login_required()
def list_announcements():
    query = Announcement.query.filter_by(is_deleted=False)
    if request.args.get("scope"):
        query = query.filter_by(scope=request.args["scope"])
    if request.args.get("target_id"):
        query = query.filter_by(target_id=int(request.args["target_id"]))
    return ok(paginate(query.order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())))


@bp.post("")
@login_required()
def create_announcement():
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    data = get_json()
    require_fields(data, ["scope", "title", "content"])
    if data["scope"] == "site" and not is_admin(actor):
        raise APIError("FORBIDDEN", "System administrator permission is required for site announcements.", 403)
    announcement = Announcement(
        scope=data["scope"],
        target_id=data.get("target_id"),
        title=data["title"],
        content=data["content"],
        publisher_id=actor.id,
        is_pinned=bool(data.get("is_pinned", False)),
    )
    db.session.add(announcement)
    db.session.flush()
    audit("create_announcement", announcement, after=announcement.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(announcement.to_dict(), status=201)


@bp.patch("/<int:announcement_id>")
@login_required()
def update_announcement(announcement_id):
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    announcement = Announcement.query.get_or_404(announcement_id)
    before = announcement.to_dict()
    update_model(announcement, get_json(), ["title", "content", "is_pinned"])
    db.session.add(announcement)
    audit("update_announcement", announcement, before=before, after=announcement.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(announcement.to_dict())


@bp.delete("/<int:announcement_id>")
@login_required()
def delete_announcement(announcement_id):
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    announcement = Announcement.query.get_or_404(announcement_id)
    before = announcement.to_dict()
    announcement.soft_delete(actor.id, get_json().get("reason"))
    db.session.add(announcement)
    audit("delete_announcement", announcement, before=before, after=announcement.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(announcement.to_dict())
