from flask import Blueprint, request

from ..extensions import db
from ..models import Announcement, Team, TeamExperiment, Topic, Year, YearMember
from ..security import current_user, is_admin, login_required, require_admin
from ..utils import APIError, audit, get_json, ok, paginate, require_fields, update_model

bp = Blueprint("years", __name__)


@bp.get("")
@login_required()
def list_years():
    query = Year.query
    if request.args.get("include_deleted") != "1" or not is_admin(current_user()):
        query = query.filter_by(is_deleted=False)
    return ok(paginate(query.order_by(Year.year_number.desc())))


@bp.post("")
@login_required()
def create_year():
    actor = current_user()
    require_admin(actor)
    data = get_json()
    require_fields(data, ["name", "year_number"])
    year = Year(name=data["name"], year_number=int(data["year_number"]), status=data.get("status", "open"))
    db.session.add(year)
    db.session.flush()
    audit("create_year", year, after=year.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(year.to_dict(), status=201)


@bp.get("/<int:year_id>")
@login_required()
def get_year(year_id):
    year = Year.query.get_or_404(year_id)
    if year.is_deleted and not is_admin(current_user()):
        raise APIError("NOT_FOUND", "Resource not found.", 404)
    data = year.to_dict()
    data["topics_count"] = Topic.query.filter_by(year_id=year_id, is_deleted=False).count()
    data["teams_count"] = Team.query.filter_by(year_id=year_id, is_deleted=False).count()
    data["experiments_count"] = TeamExperiment.query.filter_by(year_id=year_id, is_deleted=False).count()
    data["members"] = [item.to_dict() for item in YearMember.query.filter_by(year_id=year_id).all()]
    data["announcements"] = [
        item.to_dict()
        for item in Announcement.query.filter_by(scope="year", target_id=year_id, is_deleted=False)
        .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        .limit(10)
        .all()
    ]
    return ok(data)


@bp.patch("/<int:year_id>")
@login_required()
def update_year(year_id):
    actor = current_user()
    require_admin(actor)
    year = Year.query.get_or_404(year_id)
    before = year.to_dict()
    update_model(year, get_json(), ["name", "year_number", "status"])
    db.session.add(year)
    audit("update_year", year, before=before, after=year.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(year.to_dict())


@bp.post("/<int:year_id>/archive")
@login_required()
def archive_year(year_id):
    actor = current_user()
    require_admin(actor)
    year = Year.query.get_or_404(year_id)
    before = year.to_dict()
    year.status = "archived"
    db.session.add(year)
    audit("archive_year", year, before=before, after=year.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(year.to_dict())


@bp.delete("/<int:year_id>")
@login_required()
def delete_year(year_id):
    actor = current_user()
    require_admin(actor)
    year = Year.query.get_or_404(year_id)
    before = year.to_dict()
    year.soft_delete(actor.id, get_json().get("reason"))
    db.session.add(year)
    audit("delete_year", year, before=before, after=year.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(year.to_dict())


@bp.post("/<int:year_id>/members")
@login_required()
def upsert_year_member(year_id):
    actor = current_user()
    require_admin(actor)
    data = get_json()
    require_fields(data, ["user_id", "roles"])
    membership = YearMember.query.filter_by(year_id=year_id, user_id=data["user_id"]).first()
    if not membership:
        membership = YearMember(year_id=year_id, user_id=data["user_id"])
    before = membership.to_dict() if membership.id else None
    membership.role_list = data.get("roles", [])
    db.session.add(membership)
    db.session.flush()
    audit("upsert_year_member", membership, before=before, after=membership.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(membership.to_dict())
