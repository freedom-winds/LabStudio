from flask import Blueprint, request, send_file

from ..extensions import db
from ..models import ChatMember, ExperimentMember, FileAsset, TeamMember, User
from ..security import current_user, is_admin, is_teacher, login_required, require_admin
from ..utils import APIError, audit, get_json, ok, paginate, require_fields, save_upload, update_model, validate_username

bp = Blueprint("users", __name__)

VALID_GENDERS = {"男", "女"}
VALID_ACCOUNT_TYPES = {"student", "teacher", "admin"}
VALID_STATUSES = {"active", "disabled", "deleted"}
AVATAR_OWNER = "user_avatar"


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


def _student_code(username: str) -> dict | None:
    if len(username or "") != 8 or not username.isdigit() or username.startswith("0000"):
        return None
    return {
        "year": username[:4],
        "class_no": username[4:6],
        "student_no": username[6:8],
    }


def _user_statistics() -> dict:
    rows = User.query.filter(User.status != "deleted").all()
    years: dict[str, int] = {}
    classes: dict[tuple[str, str], int] = {}
    account_types: dict[str, int] = {}
    teacher_account_roles: dict[str, int] = {}
    teacher_account_total = 0
    student_code_total = 0

    for user in rows:
        account_types[user.account_type] = account_types.get(user.account_type, 0) + 1
        if user.username.startswith("0000"):
            teacher_account_total += 1
            teacher_account_roles[user.account_type] = teacher_account_roles.get(user.account_type, 0) + 1
            continue

        code = _student_code(user.username)
        if not code or user.account_type != "student":
            continue
        student_code_total += 1
        years[code["year"]] = years.get(code["year"], 0) + 1
        class_key = (code["year"], code["class_no"])
        classes[class_key] = classes.get(class_key, 0) + 1

    return {
        "total": len(rows),
        "student_code_total": student_code_total,
        "teacher_account_total": teacher_account_total,
        "account_types": account_types,
        "teacher_account_roles": teacher_account_roles,
        "years": [
            {"year": year, "count": count}
            for year, count in sorted(years.items(), key=lambda item: item[0], reverse=True)
        ],
        "classes": [
            {"year": year, "class_no": class_no, "count": count}
            for (year, class_no), count in sorted(classes.items(), key=lambda item: (-int(item[0][0]), int(item[0][1])))
        ],
    }


def _can_update_avatar(actor: User, target: User) -> bool:
    if actor.id == target.id or is_admin(actor):
        return True
    return is_teacher(actor) and target.account_type == "student"


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


@bp.get("/stats")
@login_required()
def user_stats():
    if not is_teacher(current_user()):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    return ok(_user_statistics())


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


@bp.post("/<int:user_id>/avatar")
@login_required()
def upload_user_avatar(user_id):
    actor = current_user()
    user = User.query.get_or_404(user_id)
    if not _can_update_avatar(actor, user):
        raise APIError("FORBIDDEN", "You cannot update this user's avatar.", 403)
    file = request.files.get("file")
    if not file:
        raise APIError("VALIDATION_ERROR", "Avatar file is required.", 422)

    before = user.to_dict()
    for asset in FileAsset.query.filter_by(owner_type=AVATAR_OWNER, owner_id=user.id, is_deleted=False).all():
        asset.soft_delete(actor.id, "Avatar replaced.")
        db.session.add(asset)

    meta = save_upload(file, "avatars", user.id, category="avatar")
    asset = FileAsset(owner_type=AVATAR_OWNER, owner_id=user.id, uploader_id=actor.id, **meta)
    db.session.add(asset)
    db.session.flush()
    audit("upload_user_avatar", user, before=before, after=user.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(user.to_dict())


@bp.get("/<int:user_id>/avatar")
def get_user_avatar(user_id):
    user = User.query.get_or_404(user_id)
    if user.status == "deleted":
        raise APIError("NOT_FOUND", "Resource not found.", 404)
    asset = FileAsset.query.filter_by(owner_type=AVATAR_OWNER, owner_id=user.id, is_deleted=False).order_by(FileAsset.updated_at.desc()).first()
    if not asset:
        raise APIError("NOT_FOUND", "Resource not found.", 404)
    return send_file(asset.file_path, mimetype=asset.mime_type)


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
