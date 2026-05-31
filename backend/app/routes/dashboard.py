from flask import Blueprint
from sqlalchemy import or_

from ..models import (
    Announcement,
    ChatMember,
    ChatMessage,
    ExperimentMember,
    Notification,
    Reservation,
    Team,
    TeamExperiment,
    TeamMember,
    Year,
    YearMember,
)
from ..security import current_user, is_admin, is_teacher, login_required
from ..utils import ok

bp = Blueprint("dashboard", __name__)


def _visible_team_ids(user) -> set[int] | None:
    if is_admin(user):
        return None
    team_ids = {row.team_id for row in TeamMember.query.filter_by(user_id=user.id).all()}
    team_ids.update(row.id for row in Team.query.filter_by(creator_id=user.id, is_deleted=False).all())
    year_ids = [
        row.year_id
        for row in YearMember.query.filter_by(user_id=user.id).all()
        if "year_admin" in row.role_list
    ]
    if year_ids:
        team_ids.update(
            row.id for row in Team.query.filter(Team.year_id.in_(year_ids), Team.is_deleted.is_(False)).all()
        )
    return team_ids


def _visible_experiment_query(user, team_ids: set[int] | None):
    query = TeamExperiment.query.filter(TeamExperiment.is_deleted.is_(False))
    if team_ids is None:
        return query
    experiment_ids = {row.experiment_id for row in ExperimentMember.query.filter_by(user_id=user.id).all()}
    filters = []
    if experiment_ids:
        filters.append(TeamExperiment.id.in_(experiment_ids))
    if team_ids:
        filters.append(TeamExperiment.team_id.in_(team_ids))
    return query.filter(or_(*filters)) if filters else query.filter(TeamExperiment.id == -1)


def _visible_reservation_query(user):
    query = Reservation.query
    if not is_teacher(user):
        query = query.filter_by(applicant_id=user.id)
    return query


@bp.get("")
@login_required()
def dashboard():
    user = current_user()
    team_ids = _visible_team_ids(user)
    current_year = Year.query.filter_by(status="open", is_deleted=False).order_by(Year.year_number.desc()).first()
    team_query = Team.query.filter(Team.is_deleted.is_(False))
    if team_ids is not None:
        team_query = team_query.filter(Team.id.in_(team_ids)) if team_ids else team_query.filter(Team.id == -1)
    experiment_query = _visible_experiment_query(user, team_ids)
    reservation_query = _visible_reservation_query(user)
    pending_reservations = reservation_query.filter_by(final_status="pending").count()
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
    visible_team_ids = [row.id for row in team_query.all()]
    team_member_query = TeamMember.query
    if visible_team_ids:
        team_member_query = team_member_query.filter(TeamMember.team_id.in_(visible_team_ids))
    else:
        team_member_query = team_member_query.filter(TeamMember.team_id == -1)
    unread_notifications = Notification.query.filter_by(receiver_id=user.id, is_read=False).count()
    data = {
        "user": user.to_dict(),
        "roles": {
            "account_type": user.account_type,
            "years": [row.to_dict() for row in YearMember.query.filter_by(user_id=user.id).all()],
        },
        "current_year": current_year.to_dict() if current_year else None,
        "overview": {
            "teams": len(visible_team_ids),
            "experiments": experiment_query.count(),
            "pending_reservations": pending_reservations,
            "unread_messages": unread_messages,
            "unread_notifications": unread_notifications,
        },
        "overview_details": {
            "teams": {
                "leaders": team_member_query.filter_by(role="leader").count(),
                "members": team_member_query.count(),
            },
            "experiments": {
                "working": experiment_query.filter(TeamExperiment.status.in_(["working", "ramping"])).count(),
                "completed": experiment_query.filter_by(status="completed").count(),
            },
            "reservations": {
                "pending": pending_reservations,
                "approved": reservation_query.filter_by(final_status="approved").count(),
            },
            "messages": {
                "unread_messages": unread_messages,
                "unread_notifications": unread_notifications,
            },
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
            for item in experiment_query.order_by(TeamExperiment.updated_at.desc()).limit(6).all()
        ],
        "todos": [
            item.to_dict()
            for item in reservation_query.filter_by(final_status="pending").order_by(Reservation.created_at.desc()).limit(6).all()
        ],
    }
    return ok(data)
