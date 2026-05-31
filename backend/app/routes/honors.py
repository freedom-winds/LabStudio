from flask import Blueprint, request

from ..extensions import db
from ..models import HonorMember
from ..security import current_user, is_admin, is_teacher, login_required
from ..utils import APIError, audit, get_json, ok, paginate, require_fields, update_model

bp = Blueprint("honors", __name__)


@bp.get("")
@login_required()
def list_honors():
    query = HonorMember.query
    if request.args.get("include_deleted") != "1" or not is_admin(current_user()):
        query = query.filter_by(is_deleted=False)
    return ok(paginate(query.order_by(HonorMember.sort_order.asc(), HonorMember.created_at.desc())))


@bp.post("")
@login_required()
def create_honor():
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    data = get_json()
    require_fields(data, ["name", "description"])
    honor = HonorMember(
        name=data["name"],
        description=data["description"],
        year_id=data.get("year_id"),
        image_path=data.get("image_path"),
        linked_user_id=data.get("linked_user_id"),
        sort_order=int(data.get("sort_order", 0)),
        is_visible=bool(data.get("is_visible", True)),
        creator_id=actor.id,
    )
    db.session.add(honor)
    db.session.flush()
    audit("create_honor_member", honor, after=honor.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(honor.to_dict(), status=201)


@bp.patch("/<int:honor_id>")
@login_required()
def update_honor(honor_id):
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    honor = HonorMember.query.get_or_404(honor_id)
    before = honor.to_dict()
    update_model(
        honor,
        get_json(),
        ["name", "description", "year_id", "image_path", "linked_user_id", "sort_order", "is_visible"],
    )
    db.session.add(honor)
    audit("update_honor_member", honor, before=before, after=honor.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(honor.to_dict())


@bp.post("/<int:honor_id>/hide")
@login_required()
def hide_honor(honor_id):
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    honor = HonorMember.query.get_or_404(honor_id)
    before = honor.to_dict()
    honor.is_visible = False
    db.session.add(honor)
    audit("hide_honor_member", honor, before=before, after=honor.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(honor.to_dict())


@bp.delete("/<int:honor_id>")
@login_required()
def delete_honor(honor_id):
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    honor = HonorMember.query.get_or_404(honor_id)
    before = honor.to_dict()
    honor.soft_delete(actor.id, get_json().get("reason"))
    db.session.add(honor)
    audit("delete_honor_member", honor, before=before, after=honor.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(honor.to_dict())
