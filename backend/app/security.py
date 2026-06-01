from __future__ import annotations

from functools import wraps

from flask import g, request

from .extensions import db
from .models import (
    AuthToken,
    ExperimentMember,
    Team,
    TeamExperiment,
    TeamMember,
    User,
    YearMember,
    now_iso,
)
from .utils import APIError, parse_iso


def current_user() -> User:
    user = getattr(g, "current_user", None)
    if not user:
        raise APIError("UNAUTHORIZED", "Authentication is required.", 401)
    return user


def load_user_from_token() -> User | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token_value = auth_header.removeprefix("Bearer ").strip()
    token = AuthToken.query.filter_by(token=token_value, revoked_at=None).first()
    if not token:
        return None
    if parse_iso(token.expires_at) < parse_iso(now_iso()):
        return None
    user = User.query.get(token.user_id)
    if not user or user.status in {"disabled", "deleted"}:
        return None
    return user


def login_required(allow_first_login: bool = False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = load_user_from_token()
            if not user:
                raise APIError("UNAUTHORIZED", "Authentication is required.", 401)
            if user.is_first_login and not allow_first_login:
                raise APIError("FIRST_LOGIN_REQUIRED", "Password must be changed before accessing the platform.", 403)
            g.current_user = user
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def is_admin(user: User) -> bool:
    return user.account_type == "admin"


def is_teacher(user: User) -> bool:
    return user.account_type in {"teacher", "admin"}


def is_student(user: User) -> bool:
    return user.account_type == "student"


def has_year_role(user: User, year_id: int, role: str) -> bool:
    if is_admin(user):
        return True
    membership = YearMember.query.filter_by(year_id=year_id, user_id=user.id).first()
    return bool(membership and role in membership.role_list)


def can_manage_year(user: User, year_id: int) -> bool:
    if is_admin(user):
        return True
    if is_student(user):
        return False
    return has_year_role(user, year_id, "year_admin")


def can_manage_team(user: User, team_id: int) -> bool:
    if is_admin(user):
        return True
    if is_student(user):
        return False
    team = Team.query.get(team_id)
    if not team:
        return False
    if team.creator_id == user.id:
        return True
    if can_manage_year(user, team.year_id):
        return True
    member = TeamMember.query.filter_by(team_id=team_id, user_id=user.id, role="leader").first()
    return bool(member)


def can_view_team(user: User, team_id: int) -> bool:
    if can_manage_team(user, team_id):
        return True
    return TeamMember.query.filter_by(team_id=team_id, user_id=user.id).first() is not None


def can_manage_experiment(user: User, experiment_id: int) -> bool:
    if is_admin(user):
        return True
    if is_student(user):
        return False
    experiment = TeamExperiment.query.get(experiment_id)
    if not experiment:
        return False
    if can_manage_team(user, experiment.team_id):
        return True
    member = ExperimentMember.query.filter_by(
        experiment_id=experiment_id, user_id=user.id, role="manager"
    ).first()
    return bool(member)


def can_view_experiment(user: User, experiment_id: int) -> bool:
    if can_manage_experiment(user, experiment_id):
        return True
    member = ExperimentMember.query.filter_by(experiment_id=experiment_id, user_id=user.id).first()
    return bool(member)


def require_admin(user: User) -> None:
    if not is_admin(user):
        raise APIError("FORBIDDEN", "System administrator permission is required.", 403)


def require_teacher(user: User) -> None:
    if not is_teacher(user):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)


def ensure(condition: bool, message: str = "Permission denied.") -> None:
    if not condition:
        raise APIError("FORBIDDEN", message, 403)


def revoke_token(token_value: str) -> None:
    token = AuthToken.query.filter_by(token=token_value, revoked_at=None).first()
    if token:
        token.revoked_at = now_iso()
        db.session.add(token)
