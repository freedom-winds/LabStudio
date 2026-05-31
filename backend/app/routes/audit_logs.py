from flask import Blueprint

from ..models import AuditLog, User
from ..security import current_user, is_admin, login_required
from ..utils import APIError, ok, paginate

bp = Blueprint("audit_logs", __name__)


def _log_data(log: AuditLog) -> dict:
    data = log.to_dict()
    actor = User.query.get(log.actor_id) if log.actor_id else None
    data["actor"] = (
        {
            "id": actor.id,
            "username": actor.username,
            "real_name": actor.real_name,
            "account_type": actor.account_type,
        }
        if actor
        else None
    )
    return data


@bp.get("")
@login_required()
def list_audit_logs():
    if not is_admin(current_user()):
        raise APIError("FORBIDDEN", "System administrator permission is required.", 403)
    data = paginate(AuditLog.query.order_by(AuditLog.created_at.desc()), default_per_page=80)
    data["items"] = [_log_data(AuditLog.query.get(item["id"])) for item in data["items"]]
    return ok(data)


@bp.get("/<int:log_id>")
@login_required()
def get_audit_log(log_id):
    if not is_admin(current_user()):
        raise APIError("FORBIDDEN", "System administrator permission is required.", 403)
    return ok(_log_data(AuditLog.query.get_or_404(log_id)))
