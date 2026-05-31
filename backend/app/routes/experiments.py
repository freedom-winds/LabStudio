from flask import Blueprint, request

from ..extensions import db
from ..models import (
    Announcement,
    ExperimentMember,
    Phase,
    PresentationVersion,
    Proposal,
    Step,
    StepFile,
    Team,
    TeamExperiment,
    TeamMember,
    Topic,
    User,
)
from ..security import can_manage_experiment, can_view_experiment, current_user, is_admin, login_required
from ..utils import APIError, audit, get_json, ok, paginate, require_fields, update_model

bp = Blueprint("experiments", __name__)


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
        team_ids = [m.team_id for m in TeamMember.query.filter_by(user_id=user.id).all()]
        query = query.filter((TeamExperiment.id.in_(managed_ids)) | (TeamExperiment.team_id.in_(team_ids)))
    return ok(paginate(query.order_by(TeamExperiment.updated_at.desc())))


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
