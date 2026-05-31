from flask import Blueprint

from ..models import (
    Announcement,
    ChatMember,
    ChatMessage,
    ExperimentMember,
    Notification,
    Reservation,
    TeamExperiment,
    TeamMember,
    YearMember,
)
from ..security import current_user, is_teacher, login_required
from ..utils import ok

bp = Blueprint("dashboard", __name__)


@bp.get("")
@login_required()
def dashboard():
    user = current_user()
    team_ids = [row.team_id for row in TeamMember.query.filter_by(user_id=user.id).all()]
    experiment_ids = [row.experiment_id for row in ExperimentMember.query.filter_by(user_id=user.id).all()]
    member_experiment_count = len(set(experiment_ids))
    team_experiment_count = (
        TeamExperiment.query.filter(TeamExperiment.team_id.in_(team_ids), TeamExperiment.is_deleted.is_(False)).count()
        if team_ids
        else 0
    )
    pending_reservations = (
        Reservation.query.filter_by(final_status="pending").count()
        if is_teacher(user)
        else Reservation.query.filter_by(applicant_id=user.id, final_status="pending").count()
    )
    chat_ids = [row.chat_id for row in ChatMember.query.filter_by(user_id=user.id).all()]
    unread_messages = (
        ChatMessage.query.filter(
            ChatMessage.chat_id.in_(chat_ids),
            ChatMessage.sender_id != user.id,
            ChatMessage.is_recalled.is_(False),
        ).count()
        if chat_ids
        else 0
    )
    data = {
        "user": user.to_dict(),
        "roles": {
            "account_type": user.account_type,
            "years": [row.to_dict() for row in YearMember.query.filter_by(user_id=user.id).all()],
        },
        "overview": {
            "teams": len(team_ids),
            "experiments": member_experiment_count or team_experiment_count,
            "pending_reservations": pending_reservations,
            "unread_messages": unread_messages,
            "unread_notifications": Notification.query.filter_by(receiver_id=user.id, is_read=False).count(),
        },
        "recent_announcements": [
            item.to_dict()
            for item in Announcement.query.filter_by(is_deleted=False)
            .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
            .limit(6)
            .all()
        ],
        "recent_activity": [
            item.to_dict()
            for item in TeamExperiment.query.filter_by(is_deleted=False).order_by(TeamExperiment.updated_at.desc()).limit(6).all()
        ],
        "todos": [
            item.to_dict()
            for item in Reservation.query.filter_by(final_status="pending").order_by(Reservation.created_at.desc()).limit(6).all()
        ],
    }
    return ok(data)
