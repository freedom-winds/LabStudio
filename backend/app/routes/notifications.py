from flask import Blueprint

from ..extensions import db
from ..models import Notification
from ..security import current_user, login_required
from ..utils import ok, paginate

bp = Blueprint("notifications", __name__)


@bp.get("")
@login_required()
def list_notifications():
    query = Notification.query.filter_by(receiver_id=current_user().id).order_by(Notification.created_at.desc())
    return ok(paginate(query))


@bp.post("/<int:notification_id>/read")
@login_required()
def mark_read(notification_id):
    notification = Notification.query.filter_by(id=notification_id, receiver_id=current_user().id).first_or_404()
    notification.is_read = True
    db.session.add(notification)
    db.session.commit()
    return ok(notification.to_dict())
