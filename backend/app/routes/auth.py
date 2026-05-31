from flask import Blueprint, request

from ..extensions import db
from ..models import AuthToken, User, now_iso
from ..security import current_user, login_required, revoke_token
from ..utils import APIError, audit, get_json, make_token, ok, require_fields, token_expires_at, validate_password

bp = Blueprint("auth", __name__)


@bp.post("/login")
def login():
    data = get_json()
    require_fields(data, ["username", "password"])
    user = User.query.filter_by(username=data["username"]).first()
    if not user or not user.check_password(data["password"]):
        raise APIError("INVALID_CREDENTIALS", "Username or password is incorrect.", 401)
    if user.status == "disabled":
        raise APIError("ACCOUNT_DISABLED", "This account is disabled.", 403)
    if user.status == "deleted":
        raise APIError("ACCOUNT_DELETED", "This account has been deleted.", 403)

    token = AuthToken(token=make_token(), user_id=user.id, expires_at=token_expires_at())
    user.last_login_at = now_iso()
    db.session.add(token)
    audit("login", user, after=user.to_dict(), actor_id=user.id)
    db.session.commit()
    return ok(
        {
            "token": token.token,
            "user": user.to_dict(),
            "requires_password_change": user.is_first_login,
        }
    )


@bp.post("/logout")
@login_required(allow_first_login=True)
def logout():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        revoke_token(auth_header.removeprefix("Bearer ").strip())
        audit("logout", current_user(), actor_id=current_user().id)
        db.session.commit()
    return ok({"status": "logged_out"})


@bp.get("/me")
@login_required(allow_first_login=True)
def me():
    user = current_user()
    return ok({"user": user.to_dict()})


@bp.post("/first-password")
@login_required(allow_first_login=True)
def first_password():
    user = current_user()
    data = get_json()
    require_fields(data, ["new_password"])
    if not user.is_first_login:
        raise APIError("NOT_FIRST_LOGIN", "First login password change is already completed.", 409)
    validate_password(data["new_password"])
    before = user.to_dict()
    user.set_password(data["new_password"])
    user.is_first_login = False
    db.session.add(user)
    audit("first_password_change", user, before=before, after=user.to_dict(), actor_id=user.id)
    db.session.commit()
    return ok({"user": user.to_dict()})


@bp.post("/password")
@login_required()
def change_password():
    user = current_user()
    data = get_json()
    require_fields(data, ["old_password", "new_password"])
    if not user.check_password(data["old_password"]):
        raise APIError("INVALID_PASSWORD", "Old password is incorrect.", 422)
    validate_password(data["new_password"])
    user.set_password(data["new_password"])
    db.session.add(user)
    audit("password_change", user, actor_id=user.id)
    db.session.commit()
    return ok({"status": "changed"})
