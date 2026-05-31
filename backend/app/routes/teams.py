from flask import Blueprint, request

from ..extensions import db
from ..models import (
    Chat,
    ChatMember,
    ExperimentMember,
    Team,
    TeamExperiment,
    TeamMember,
    TeamTopic,
    Topic,
    User,
    Year,
)
from ..security import can_manage_team, current_user, is_admin, is_teacher, login_required
from ..utils import APIError, audit, get_json, ok, paginate, require_fields, update_model

bp = Blueprint("teams", __name__)


def _sync_chat_member(chat_id: int, user_id: int) -> None:
    if not ChatMember.query.filter_by(chat_id=chat_id, user_id=user_id).first():
        db.session.add(ChatMember(chat_id=chat_id, user_id=user_id))


def _get_or_create_team_chat(team: Team) -> Chat:
    chat = Chat.query.filter_by(chat_type="team", team_id=team.id).first()
    if not chat:
        chat = Chat(chat_type="team", year_id=team.year_id, team_id=team.id, title=f"{team.name} 群聊")
        db.session.add(chat)
        db.session.flush()
    return chat


def _get_or_create_experiment_chat(experiment: TeamExperiment) -> Chat:
    chat = Chat.query.filter_by(chat_type="experiment", experiment_id=experiment.id).first()
    if not chat:
        chat = Chat(
            chat_type="experiment",
            year_id=experiment.year_id,
            team_id=experiment.team_id,
            experiment_id=experiment.id,
            title=f"{experiment.name} 群聊",
        )
        db.session.add(chat)
        db.session.flush()
    return chat


def _create_experiment_for_topic(team: Team, topic: Topic, actor_id: int) -> TeamExperiment:
    experiment = TeamExperiment.query.filter_by(team_id=team.id, topic_id=topic.id).first()
    if not experiment:
        experiment = TeamExperiment(
            year_id=team.year_id,
            team_id=team.id,
            topic_id=topic.id,
            name=topic.title,
            status="working",
        )
        db.session.add(experiment)
        db.session.flush()
        chat = _get_or_create_experiment_chat(experiment)
        for member in TeamMember.query.filter_by(team_id=team.id).all():
            role = "manager" if member.role == "leader" else "participant"
            if not ExperimentMember.query.filter_by(experiment_id=experiment.id, user_id=member.user_id).first():
                db.session.add(ExperimentMember(experiment_id=experiment.id, user_id=member.user_id, role=role))
            _sync_chat_member(chat.id, member.user_id)
        audit("create_team_experiment", experiment, after=experiment.to_dict(), actor_id=actor_id)
    elif experiment.is_deleted:
        experiment.is_deleted = False
        experiment.deleted_by = None
        experiment.deleted_at = None
        experiment.delete_reason = None
    return experiment


@bp.get("")
@login_required()
def list_teams():
    query = Team.query
    if request.args.get("include_deleted") != "1" or not is_admin(current_user()):
        query = query.filter_by(is_deleted=False)
    if request.args.get("year_id"):
        query = query.filter_by(year_id=int(request.args["year_id"]))
    return ok(paginate(query.order_by(Team.created_at.desc())))


@bp.post("")
@login_required()
def create_team():
    actor = current_user()
    if not is_teacher(actor):
        raise APIError("FORBIDDEN", "Teacher permission is required.", 403)
    data = get_json()
    require_fields(data, ["year_id", "name"])
    year = Year.query.get_or_404(data["year_id"])
    if year.status == "archived":
        raise APIError("YEAR_ARCHIVED", "Archived years cannot accept new teams.", 409)

    team = Team(
        year_id=year.id,
        name=data["name"],
        description=data.get("description", ""),
        status=data.get("status", "active"),
        creator_id=actor.id,
    )
    db.session.add(team)
    db.session.flush()
    chat = _get_or_create_team_chat(team)

    for member_data in data.get("members", []):
        user_id = int(member_data["user_id"])
        role = member_data.get("role", "member")
        db.session.add(TeamMember(team_id=team.id, user_id=user_id, role=role))
        _sync_chat_member(chat.id, user_id)

    for topic_id in data.get("topic_ids", []):
        topic = Topic.query.filter_by(id=topic_id, year_id=year.id, is_deleted=False, status="active").first()
        if not topic:
            continue
        db.session.add(TeamTopic(team_id=team.id, topic_id=topic.id, is_active=True))
        _create_experiment_for_topic(team, topic, actor.id)

    audit("create_team", team, after=team.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(team.to_dict(), status=201)


@bp.get("/<int:team_id>")
@login_required()
def get_team(team_id):
    team = Team.query.get_or_404(team_id)
    if team.is_deleted and not is_admin(current_user()):
        raise APIError("NOT_FOUND", "Resource not found.", 404)
    data = team.to_dict()
    data["members"] = [
        {**member.to_dict(), "user": User.query.get(member.user_id).to_dict()}
        for member in TeamMember.query.filter_by(team_id=team.id).all()
    ]
    topic_links = TeamTopic.query.filter_by(team_id=team.id, is_active=True).all()
    data["topics"] = [Topic.query.get(link.topic_id).to_dict() for link in topic_links if Topic.query.get(link.topic_id)]
    data["experiments"] = [
        item.to_dict()
        for item in TeamExperiment.query.filter_by(team_id=team.id, is_deleted=False)
        .order_by(TeamExperiment.updated_at.desc())
        .all()
    ]
    return ok(data)


@bp.patch("/<int:team_id>")
@login_required()
def update_team(team_id):
    actor = current_user()
    if not can_manage_team(actor, team_id):
        raise APIError("FORBIDDEN", "Team management permission is required.", 403)
    team = Team.query.get_or_404(team_id)
    before = team.to_dict()
    update_model(
        team,
        get_json(),
        ["name", "description", "status", "final_competition_level", "final_award_level", "award_description"],
    )
    db.session.add(team)
    audit("update_team", team, before=before, after=team.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(team.to_dict())


@bp.delete("/<int:team_id>")
@login_required()
def delete_team(team_id):
    actor = current_user()
    if not can_manage_team(actor, team_id):
        raise APIError("FORBIDDEN", "Team management permission is required.", 403)
    team = Team.query.get_or_404(team_id)
    before = team.to_dict()
    team.soft_delete(actor.id, get_json().get("reason"))
    for experiment in TeamExperiment.query.filter_by(team_id=team.id, is_deleted=False).all():
        experiment.soft_delete(actor.id, "Parent team deleted.")
    db.session.add(team)
    audit("delete_team", team, before=before, after=team.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(team.to_dict())


@bp.post("/<int:team_id>/members")
@login_required()
def upsert_team_member(team_id):
    actor = current_user()
    if not can_manage_team(actor, team_id):
        raise APIError("FORBIDDEN", "Team management permission is required.", 403)
    data = get_json()
    require_fields(data, ["user_id"])
    User.query.get_or_404(data["user_id"])
    member = TeamMember.query.filter_by(team_id=team_id, user_id=data["user_id"]).first()
    if not member:
        member = TeamMember(team_id=team_id, user_id=data["user_id"])
    before = member.to_dict() if member.id else None
    member.role = data.get("role", member.role or "member")
    db.session.add(member)
    db.session.flush()
    chat = _get_or_create_team_chat(Team.query.get(team_id))
    _sync_chat_member(chat.id, member.user_id)
    audit("upsert_team_member", member, before=before, after=member.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(member.to_dict())


@bp.delete("/<int:team_id>/members/<int:user_id>")
@login_required()
def remove_team_member(team_id, user_id):
    actor = current_user()
    if not can_manage_team(actor, team_id):
        raise APIError("FORBIDDEN", "Team management permission is required.", 403)
    member = TeamMember.query.filter_by(team_id=team_id, user_id=user_id).first_or_404()
    before = member.to_dict()
    db.session.delete(member)
    audit("remove_team_member", member, before=before, actor_id=actor.id)
    db.session.commit()
    return ok({"removed": user_id})


@bp.post("/<int:team_id>/topics")
@login_required()
def set_team_topics(team_id):
    actor = current_user()
    if not can_manage_team(actor, team_id):
        raise APIError("FORBIDDEN", "Team management permission is required.", 403)
    team = Team.query.get_or_404(team_id)
    data = get_json()
    topic_ids = set(int(item) for item in data.get("topic_ids", []))

    for link in TeamTopic.query.filter_by(team_id=team_id).all():
        link.is_active = link.topic_id in topic_ids
    for topic_id in topic_ids:
        topic = Topic.query.filter_by(id=topic_id, year_id=team.year_id, is_deleted=False).first_or_404()
        link = TeamTopic.query.filter_by(team_id=team_id, topic_id=topic_id).first()
        if not link:
            db.session.add(TeamTopic(team_id=team_id, topic_id=topic_id, is_active=True))
        else:
            link.is_active = True
        _create_experiment_for_topic(team, topic, actor.id)
    audit("set_team_topics", team, after={"topic_ids": list(topic_ids)}, actor_id=actor.id)
    db.session.commit()
    return get_team(team_id)


@bp.post("/<int:team_id>/end")
@login_required()
def end_team(team_id):
    actor = current_user()
    if not can_manage_team(actor, team_id):
        raise APIError("FORBIDDEN", "Team management permission is required.", 403)
    data = get_json()
    require_fields(data, ["final_competition_level", "final_award_level"])
    team = Team.query.get_or_404(team_id)
    before = team.to_dict()
    team.status = "ended"
    team.final_competition_level = data["final_competition_level"]
    team.final_award_level = data["final_award_level"]
    team.award_description = data.get("award_description", "")
    db.session.add(team)
    audit("end_team", team, before=before, after=team.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(team.to_dict())
