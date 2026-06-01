from flask import Blueprint, request

from ..extensions import db
from ..models import ChatMember, ExperimentMember, TeamMember, User
from ..security import current_user, is_admin, is_teacher, login_required, require_admin
from ..utils import APIError, audit, get_json, ok, paginate, require_fields, update_model, validate_username

bp = Blueprint("users", __name__)

VALID_GENDERS = {"男", "女"}
VALID_ACCOUNT_TYPES = {"student", "teacher", "admin"}
VALID_STATUSES = {"active", "disabled", "deleted"}


def _remove_user_assignments(user_id: int) -> dict:
    team_member_ids = [row.id for row in TeamMember.query.filter_by(user_id=user_id).all()]
    experiment_member_ids = [row.id for row in ExperimentMember.query.filter_by(user_id=user_id).all()]
    chat_member_ids = [row.id for row in ChatMember.query.filter_by(user_id=user_id).all()]
    TeamMember.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    ExperimentMember.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    ChatMember.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    return {
        "removed_team_member_ids": team_member_ids,
        "removed_experiment_member_ids": experiment_member_ids,
        "removed_chat_member_ids": chat_member_ids,
    }


@bp.get("")
@login_required()
def list_users():
    user = current_user()
    query = User.query
    if request.args.get("include_deleted") != "1" or not is_admin(user):
        query = query.filter(User.status != "deleted")
    keyword = request.args.get("q")
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((User.username.like(like)) | (User.real_name.like(like)))
    return ok(paginate(query.order_by(User.created_at.desc())))


@bp.post("")
@login_required()
def create_user():
    actor = current_user()
    data = get_json()
    require_fields(data, ["username", "real_name", "gender", "account_type"])
    validate_username(data["username"])
    if data["gender"] not in VALID_GENDERS:
        raise APIError("INVALID_GENDER", "Gender must be 男 or 女.", 422)
    if data["account_type"] not in VALID_ACCOUNT_TYPES:
        raise APIError("INVALID_ACCOUNT_TYPE", "Invalid account type.", 422)
    if data["account_type"] in {"teacher", "admin"}:
        require_admin(actor)
    elif not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required to create student accounts.", 403)
    if User.query.filter_by(username=data["username"]).first():
        raise APIError("USERNAME_EXISTS", "Username already exists.", 409)

    user = User(
        username=data["username"],
        real_name=data["real_name"],
        gender=data["gender"],
        account_type=data["account_type"],
        status="active",
        is_first_login=True,
    )
    user.set_password(data["username"])
    db.session.add(user)
    db.session.flush()
    audit("create_user", user, after=user.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(user.to_dict(), status=201)


@bp.get("/<int:user_id>")
@login_required()
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.status == "deleted" and not is_admin(current_user()):
        raise APIError("NOT_FOUND", "Resource not found.", 404)
    return ok(user.to_dict())


@bp.patch("/<int:user_id>")
@login_required()
def update_user(user_id):
    actor = current_user()
    user = User.query.get_or_404(user_id)
    data = get_json()
    if not is_admin(actor):
        if not is_teacher(actor) or user.account_type != "student":
            raise APIError("FORBIDDEN", "Only system administrators can update this user.", 403)
        forbidden_fields = set(data) - {"real_name", "gender"}
        if forbidden_fields:
            raise APIError("FORBIDDEN", "Teachers can only update student profile fields.", 403)

    if "gender" in data and data["gender"] not in VALID_GENDERS:
        raise APIError("INVALID_GENDER", "Gender must be 男 or 女.", 422)
    if "account_type" in data and data["account_type"] not in VALID_ACCOUNT_TYPES:
        raise APIError("INVALID_ACCOUNT_TYPE", "Invalid account type.", 422)
    if "status" in data and data["status"] not in VALID_STATUSES:
        raise APIError("INVALID_STATUS", "Invalid user status.", 422)

    before = user.to_dict()
    update_model(user, data, ["real_name", "gender", "status", "account_type"])
    db.session.add(user)
    audit("update_user", user, before=before, after=user.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(user.to_dict())


@bp.post("/<int:user_id>/disable")
@login_required()
def disable_user(user_id):
    actor = current_user()
    require_admin(actor)
    user = User.query.get_or_404(user_id)
    before = user.to_dict()
    user.status = "disabled"
    db.session.add(user)
    audit("disable_user", user, before=before, after=user.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(user.to_dict())


@bp.delete("/<int:user_id>")
@login_required()
def delete_user(user_id):
    actor = current_user()
    require_admin(actor)
    user = User.query.get_or_404(user_id)
    before = user.to_dict()
    cleanup = _remove_user_assignments(user.id)
    user.soft_delete(actor.id, get_json().get("reason"))
    db.session.add(user)
    audit("delete_user", user, before=before, after={**user.to_dict(), **cleanup}, actor_id=actor.id)
    db.session.commit()
    return ok(user.to_dict())
