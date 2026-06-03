from flask import Blueprint, request

from ..extensions import db
from ..models import Reservation, ReservationApproval, User
from ..security import current_user, is_teacher, login_required
from ..utils import APIError, audit, get_json, ok, paginate, require_fields

bp = Blueprint("reservations", __name__)


def _user_summary(user_id: int | None) -> dict | None:
    if not user_id:
        return None
    user = User.query.get(user_id)
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "account_type": user.account_type,
        "avatar_url": user.to_dict().get("avatar_url", ""),
    }


def _serialize_reservation(reservation: Reservation) -> dict:
    data = reservation.to_dict()
    data["applicant"] = _user_summary(reservation.applicant_id)
    data["duty_teacher"] = _user_summary(reservation.duty_teacher_id)
    data["approvals"] = [
        {**approval.to_dict(), "teacher": _user_summary(approval.teacher_id)}
        for approval in ReservationApproval.query.filter_by(reservation_id=reservation.id)
        .order_by(ReservationApproval.updated_at.desc())
        .all()
    ]
    return data


def _teachers():
    return User.query.filter_by(account_type="teacher", status="active").order_by(User.username.asc()).limit(2).all()


@bp.get("")
@login_required()
def list_reservations():
    actor = current_user()
    query = Reservation.query
    if not is_teacher(actor):
        query = query.filter_by(applicant_id=actor.id)
    if request.args.get("status"):
        query = query.filter_by(final_status=request.args["status"])
    data = paginate(query.order_by(Reservation.start_time.desc()))
    data["items"] = [_serialize_reservation(Reservation.query.get(item["id"])) for item in data["items"]]
    return ok(data)


@bp.post("")
@login_required()
def create_reservation():
    actor = current_user()
    data = get_json()
    require_fields(data, ["start_time", "end_time", "purpose"])
    reservation = Reservation(
        applicant_id=actor.id,
        year_id=data.get("year_id"),
        team_id=data.get("team_id"),
        experiment_id=data.get("experiment_id"),
        start_time=data["start_time"],
        end_time=data["end_time"],
        purpose=data["purpose"],
        participants_note=data.get("participants_note", ""),
    )
    db.session.add(reservation)
    db.session.flush()
    for teacher in _teachers():
        db.session.add(ReservationApproval(reservation_id=reservation.id, teacher_id=teacher.id))
    audit("create_reservation", reservation, after=reservation.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(_serialize_reservation(reservation), status=201)


@bp.get("/<int:reservation_id>")
@login_required()
def get_reservation(reservation_id):
    actor = current_user()
    reservation = Reservation.query.get_or_404(reservation_id)
    if not (is_teacher(actor) or reservation.applicant_id == actor.id):
        raise APIError("FORBIDDEN", "Reservation access is required.", 403)
    return ok(_serialize_reservation(reservation))


@bp.post("/<int:reservation_id>/cancel")
@login_required()
def cancel_reservation(reservation_id):
    actor = current_user()
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.applicant_id != actor.id:
        raise APIError("FORBIDDEN", "Only the applicant can cancel this reservation.", 403)
    if reservation.final_status != "pending":
        raise APIError("INVALID_STATUS", "Only pending reservations can be cancelled.", 409)
    before = reservation.to_dict()
    reservation.final_status = "cancelled"
    db.session.add(reservation)
    audit("cancel_reservation", reservation, before=before, after=reservation.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(reservation.to_dict())


@bp.delete("/<int:reservation_id>")
@login_required()
def delete_reservation(reservation_id):
    actor = current_user()
    reservation = Reservation.query.get_or_404(reservation_id)
    if not (is_teacher(actor) or reservation.applicant_id == actor.id):
        raise APIError("FORBIDDEN", "Reservation delete permission is required.", 403)
    approvals = ReservationApproval.query.filter_by(reservation_id=reservation.id).all()
    before = reservation.to_dict()
    before["approvals"] = [item.to_dict() for item in approvals]
    for approval in approvals:
        db.session.delete(approval)
    audit("delete_reservation", reservation, before=before, actor_id=actor.id)
    db.session.delete(reservation)
    db.session.commit()
    return ok({"removed": reservation_id})


@bp.post("/<int:reservation_id>/approve")
@login_required()
def approve_reservation(reservation_id):
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    data = get_json()
    require_fields(data, ["status"])
    if data["status"] not in {"approved", "rejected"}:
        raise APIError("INVALID_STATUS", "Approval status must be approved or rejected.", 422)
    reservation = Reservation.query.get_or_404(reservation_id)
    approval = ReservationApproval.query.filter_by(reservation_id=reservation.id, teacher_id=actor.id).first()
    if not approval:
        approval = ReservationApproval(reservation_id=reservation.id, teacher_id=actor.id)
    before = reservation.to_dict()
    approval.status = data["status"]
    approval.comment = data.get("comment", "")
    db.session.add(approval)
    reservation.final_status = data["status"]
    reservation.duty_teacher_id = actor.id if data["status"] == "approved" else None
    db.session.add(reservation)
    audit("approve_reservation", reservation, before=before, after=reservation.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(_serialize_reservation(reservation))
