from flask import Blueprint, request
from sqlalchemy import or_

from ..extensions import db
from ..models import (
    Announcement,
    Chat,
    ChatMember,
    ExperimentMember,
    Phase,
    PresentationVersion,
    Proposal,
    Step,
    StepFile,
    Team,
    TeamExperiment,
    TeamMember,
    TeamTopic,
    Topic,
    User,
    YearMember,
)
from ..security import can_manage_experiment, can_manage_team, can_view_experiment, current_user, is_admin, login_required
from ..utils import APIError, audit, get_json, ok, paginate, require_fields, update_model

bp = Blueprint("experiments", __name__)


def _sync_chat_member(chat_id: int, user_id: int) -> None:
    if not ChatMember.query.filter_by(chat_id=chat_id, user_id=user_id).first():
        db.session.add(ChatMember(chat_id=chat_id, user_id=user_id))


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


def _visible_team_ids(user) -> set[int]:
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


def _with_references(data: dict) -> dict:
    team = Team.query.get(data["team_id"])
    topic = Topic.query.get(data["topic_id"])
    data["team"] = team.to_dict() if team else None
    data["topic"] = topic.to_dict() if topic else None
    return data


def _sync_experiment_members(experiment: TeamExperiment, actor_id: int) -> None:
    team = Team.query.get(experiment.team_id)
    member_roles = {}
    if team:
        member_roles[team.creator_id] = "manager"
    member_roles[actor_id] = "manager"
    for member in TeamMember.query.filter_by(team_id=experiment.team_id).all():
        member_roles[member.user_id] = "manager" if member.role == "leader" else "participant"

    chat = _get_or_create_experiment_chat(experiment)
    for user_id, role in member_roles.items():
        existing = ExperimentMember.query.filter_by(experiment_id=experiment.id, user_id=user_id).first()
        if not existing:
            db.session.add(ExperimentMember(experiment_id=experiment.id, user_id=user_id, role=role))
        elif existing.role != "manager" and role == "manager":
            existing.role = "manager"
        _sync_chat_member(chat.id, user_id)


@bp.get("")
@login_required()
def list_experiments():
    user = current_user()
    query = TeamExperiment.query
    if request.args.get("include_deleted") != "1" or not is_admin(user):
        query = query.filter_by(is_deleted=False)
    if request.args.get("team_id"):
        query = query.filter_by(team_id=int(request.args["team_id"]))
    if request.args.get("year_id"):
        query = query.filter_by(year_id=int(request.args["year_id"]))
    if not is_admin(user):
        managed_ids = [m.experiment_id for m in ExperimentMember.query.filter_by(user_id=user.id).all()]
        team_ids = _visible_team_ids(user)
        filters = []
        if managed_ids:
            filters.append(TeamExperiment.id.in_(managed_ids))
        if team_ids:
            filters.append(TeamExperiment.team_id.in_(team_ids))
        query = query.filter(or_(*filters)) if filters else query.filter(TeamExperiment.id == -1)
    data = paginate(query.order_by(TeamExperiment.updated_at.desc()))
    data["items"] = [_with_references(item) for item in data["items"]]
    return ok(data)


@bp.post("")
@login_required()
def create_experiment():
    actor = current_user()
    data = get_json()
    require_fields(data, ["team_id", "topic_id"])
    team = Team.query.get_or_404(int(data["team_id"]))
    if team.is_deleted:
        raise APIError("TEAM_DELETED", "Deleted teams cannot accept new experiments.", 409)
    if not can_manage_team(actor, team.id):
        raise APIError("FORBIDDEN", "Team management permission is required.", 403)
    topic = Topic.query.filter_by(id=int(data["topic_id"]), year_id=team.year_id, is_deleted=False).first()
    if not topic:
        raise APIError("INVALID_TOPIC", "Topic must belong to the selected team year.", 422)
    if topic.status != "active":
        raise APIError("TOPIC_DISABLED", "Disabled topics cannot create experiments.", 409)

    link = TeamTopic.query.filter_by(team_id=team.id, topic_id=topic.id).first()
    if not link:
        db.session.add(TeamTopic(team_id=team.id, topic_id=topic.id, is_active=True))
    else:
        link.is_active = True

    experiment = TeamExperiment.query.filter_by(team_id=team.id, topic_id=topic.id).first()
    status = data.get("status", "working")
    if status not in {"working", "ramping", "completed", "abandoned"}:
        raise APIError("INVALID_STATUS", "Invalid experiment status.", 422)
    created = False
    if not experiment:
        experiment = TeamExperiment(
            year_id=team.year_id,
            team_id=team.id,
            topic_id=topic.id,
            name=data.get("name") or topic.title,
            status=status,
        )
        db.session.add(experiment)
        db.session.flush()
        created = True
    elif experiment.is_deleted:
        experiment.is_deleted = False
        experiment.deleted_by = None
        experiment.deleted_at = None
        experiment.delete_reason = None
        experiment.name = data.get("name") or experiment.name or topic.title
        experiment.status = status
        created = True

    _sync_experiment_members(experiment, actor.id)
    audit(
        "create_experiment" if created else "reuse_experiment",
        experiment,
        after=experiment.to_dict(),
        actor_id=actor.id,
    )
    db.session.commit()
    return ok(_with_references(experiment.to_dict()), status=201 if created else 200)


@bp.get("/<int:experiment_id>")
@login_required()
def get_experiment(experiment_id):
    actor = current_user()
    experiment = TeamExperiment.query.get_or_404(experiment_id)
    if experiment.is_deleted and not is_admin(actor):
        raise APIError("NOT_FOUND", "Resource not found.", 404)
    if not can_view_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment access is required.", 403)
    phases = Phase.query.filter_by(experiment_id=experiment_id, is_deleted=False).order_by(Phase.sort_order.asc()).all()
    phase_ids = [phase.id for phase in phases]
    steps = Step.query.filter(Step.phase_id.in_(phase_ids), Step.is_deleted.is_(False)).all() if phase_ids else []
    data = experiment.to_dict()
    data["team"] = Team.query.get(experiment.team_id).to_dict() if Team.query.get(experiment.team_id) else None
    data["topic"] = Topic.query.get(experiment.topic_id).to_dict() if Topic.query.get(experiment.topic_id) else None
    data["members"] = [
        {**member.to_dict(), "user": User.query.get(member.user_id).to_dict()}
        for member in ExperimentMember.query.filter_by(experiment_id=experiment_id).all()
    ]
    data["summary"] = {
        "phase_count": len(phases),
        "step_count": len(steps),
        "completed_step_count": len([step for step in steps if step.status == "done"]),
        "file_count": StepFile.query.filter(StepFile.step_id.in_([step.id for step in steps]), StepFile.is_deleted.is_(False)).count()
        if steps
        else 0,
        "proposal_count": Proposal.query.filter_by(experiment_id=experiment_id).count(),
        "latest_presentation": (
            PresentationVersion.query.filter_by(experiment_id=experiment_id, is_hidden=False)
            .order_by(PresentationVersion.is_current.desc(), PresentationVersion.version_no.desc())
            .first()
            .to_dict()
            if PresentationVersion.query.filter_by(experiment_id=experiment_id, is_hidden=False).first()
            else None
        ),
    }
    data["announcements"] = [
        item.to_dict()
        for item in Announcement.query.filter_by(scope="experiment", target_id=experiment_id, is_deleted=False)
        .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        .limit(5)
        .all()
    ]
    return ok(data)


@bp.patch("/<int:experiment_id>")
@login_required()
def update_experiment(experiment_id):
    actor = current_user()
    if not can_manage_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    experiment = TeamExperiment.query.get_or_404(experiment_id)
    before = experiment.to_dict()
    update_model(experiment, get_json(), ["name", "status"])
    db.session.add(experiment)
    audit("update_experiment", experiment, before=before, after=experiment.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(experiment.to_dict())


@bp.post("/<int:experiment_id>/status")
@login_required()
def update_status(experiment_id):
    data = get_json()
    data["status"] = data.get("status")
    return update_experiment(experiment_id)


@bp.delete("/<int:experiment_id>")
@login_required()
def delete_experiment(experiment_id):
    actor = current_user()
    if not can_manage_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    experiment = TeamExperiment.query.get_or_404(experiment_id)
    before = experiment.to_dict()
    experiment.soft_delete(actor.id, get_json().get("reason"))
    db.session.add(experiment)
    audit("delete_experiment", experiment, before=before, after=experiment.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(experiment.to_dict())


@bp.post("/<int:experiment_id>/members")
@login_required()
def upsert_experiment_member(experiment_id):
    actor = current_user()
    if not can_manage_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    data = get_json()
    require_fields(data, ["user_id", "role"])
    if data["role"] not in {"manager", "participant", "observer"}:
        raise APIError("INVALID_ROLE", "Invalid experiment role.", 422)
    member = ExperimentMember.query.filter_by(experiment_id=experiment_id, user_id=data["user_id"]).first()
    if not member:
        member = ExperimentMember(experiment_id=experiment_id, user_id=data["user_id"])
    before = member.to_dict() if member.id else None
    member.role = data["role"]
    db.session.add(member)
    db.session.flush()
    audit("upsert_experiment_member", member, before=before, after=member.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(member.to_dict())


@bp.delete("/<int:experiment_id>/members/<int:user_id>")
@login_required()
def remove_experiment_member(experiment_id, user_id):
    actor = current_user()
    if not can_manage_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    member = ExperimentMember.query.filter_by(experiment_id=experiment_id, user_id=user_id).first_or_404()
    before = member.to_dict()
    db.session.delete(member)
    audit("remove_experiment_member", member, before=before, actor_id=actor.id)
    db.session.commit()
    return ok({"removed": user_id})
