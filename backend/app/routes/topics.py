from flask import Blueprint, request

from ..extensions import db
from ..models import TeamExperiment, Topic, Year
from ..security import current_user, is_admin, is_teacher, login_required
from ..utils import APIError, audit, get_json, ok, paginate, require_fields, update_model

bp = Blueprint("topics", __name__)


@bp.get("")
@login_required()
def list_topics():
    query = Topic.query
    if request.args.get("include_deleted") != "1" or not is_admin(current_user()):
        query = query.filter_by(is_deleted=False)
    if request.args.get("year_id"):
        query = query.filter_by(year_id=int(request.args["year_id"]))
    return ok(paginate(query.order_by(Topic.created_at.desc())))


@bp.post("")
@login_required()
def create_topic():
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    data = get_json()
    require_fields(data, ["year_id", "title"])
    year = Year.query.get_or_404(data["year_id"])
    if year.status == "archived":
        raise APIError("YEAR_ARCHIVED", "Archived years cannot accept new topics.", 409)
    topic = Topic(
        year_id=year.id,
        title=data["title"],
        description=data.get("description", ""),
        status=data.get("status", "active"),
        creator_id=actor.id,
    )
    db.session.add(topic)
    db.session.flush()
    audit("create_topic", topic, after=topic.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(topic.to_dict(), status=201)


@bp.get("/<int:topic_id>")
@login_required()
def get_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if topic.is_deleted and not is_admin(current_user()):
        raise APIError("NOT_FOUND", "Resource not found.", 404)
    data = topic.to_dict()
    data["selected_team_count"] = TeamExperiment.query.filter_by(topic_id=topic.id, is_deleted=False).count()
    return ok(data)


@bp.patch("/<int:topic_id>")
@login_required()
def update_topic(topic_id):
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    topic = Topic.query.get_or_404(topic_id)
    before = topic.to_dict()
    update_model(topic, get_json(), ["title", "description", "status"])
    db.session.add(topic)
    audit("update_topic", topic, before=before, after=topic.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(topic.to_dict())


@bp.post("/<int:topic_id>/disable")
@login_required()
def disable_topic(topic_id):
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    topic = Topic.query.get_or_404(topic_id)
    before = topic.to_dict()
    topic.status = "disabled"
    db.session.add(topic)
    audit("disable_topic", topic, before=before, after=topic.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(topic.to_dict())


@bp.delete("/<int:topic_id>")
@login_required()
def delete_topic(topic_id):
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    topic = Topic.query.get_or_404(topic_id)
    before = topic.to_dict()
    topic.soft_delete(actor.id, get_json().get("reason"))
    db.session.add(topic)
    audit("delete_topic", topic, before=before, after=topic.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(topic.to_dict())
