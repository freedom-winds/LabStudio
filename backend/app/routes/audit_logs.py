from flask import Blueprint

from ..models import AuditLog
from ..security import current_user, is_admin, login_required
from ..utils import APIError, ok, paginate

bp = Blueprint("audit_logs", __name__)


@bp.get("")
@login_required()
def list_audit_logs():
    if not is_admin(current_user()):
        raise APIError("FORBIDDEN", "System administrator permission is required.", 403)
    return ok(paginate(AuditLog.query.order_by(AuditLog.created_at.desc()), default_per_page=80))


@bp.get("/<int:log_id>")
@login_required()
def get_audit_log(log_id):
    if not is_admin(current_user()):
        raise APIError("FORBIDDEN", "System administrator permission is required.", 403)
    return ok(AuditLog.query.get_or_404(log_id).to_dict())
