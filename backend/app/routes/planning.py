from flask import Blueprint

from ..extensions import db
from ..models import Phase, Step
from ..security import can_view_experiment, current_user, login_required
from ..utils import APIError, audit, get_json, ok, require_fields, update_model

bp = Blueprint("planning", __name__)

# Plan maintenance is an in-experiment activity: any experiment member may edit it.
can_manage_experiment = can_view_experiment


def _phase_or_404(phase_id: int) -> Phase:
    return Phase.query.get_or_404(phase_id)


def _step_or_404(step_id: int) -> Step:
    return Step.query.get_or_404(step_id)


@bp.get("/experiments/<int:experiment_id>/phases")
@login_required()
def list_phases(experiment_id):
    if not can_view_experiment(current_user(), experiment_id):
        raise APIError("FORBIDDEN", "Experiment access is required.", 403)
    phases = Phase.query.filter_by(experiment_id=experiment_id, is_deleted=False).order_by(Phase.sort_order.asc()).all()
    data = []
    for phase in phases:
        item = phase.to_dict()
        item["steps"] = [
            step.to_dict()
            for step in Step.query.filter_by(phase_id=phase.id, is_deleted=False).order_by(Step.sort_order.asc()).all()
        ]
        data.append(item)
    return ok(data)


@bp.post("/experiments/<int:experiment_id>/phases")
@login_required()
def create_phase(experiment_id):
    actor = current_user()
    if not can_manage_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    data = get_json()
    require_fields(data, ["title"])
    next_order = Phase.query.filter_by(experiment_id=experiment_id, is_deleted=False).count() + 1
    phase = Phase(
        experiment_id=experiment_id,
        title=data["title"],
        goal=data.get("goal", ""),
        expected_start_date=data.get("expected_start_date"),
        expected_end_date=data.get("expected_end_date"),
        sort_order=int(data.get("sort_order", next_order)),
        creator_id=actor.id,
    )
    db.session.add(phase)
    db.session.flush()
    audit("create_phase", phase, after=phase.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(phase.to_dict(), status=201)


@bp.patch("/phases/<int:phase_id>")
@login_required()
def update_phase(phase_id):
    actor = current_user()
    phase = _phase_or_404(phase_id)
    if not can_manage_experiment(actor, phase.experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    before = phase.to_dict()
    update_model(phase, get_json(), ["title", "goal", "expected_start_date", "expected_end_date", "sort_order"])
    db.session.add(phase)
    audit("update_phase", phase, before=before, after=phase.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(phase.to_dict())


@bp.delete("/phases/<int:phase_id>")
@login_required()
def delete_phase(phase_id):
    actor = current_user()
    phase = _phase_or_404(phase_id)
    if not can_manage_experiment(actor, phase.experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    before = phase.to_dict()
    phase.soft_delete(actor.id, get_json().get("reason"))
    for step in Step.query.filter_by(phase_id=phase.id, is_deleted=False).all():
        step.soft_delete(actor.id, "Parent phase deleted.")
    db.session.add(phase)
    audit("delete_phase", phase, before=before, after=phase.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(phase.to_dict())


@bp.post("/experiments/<int:experiment_id>/phases/reorder")
@login_required()
def reorder_phases(experiment_id):
    actor = current_user()
    if not can_manage_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    ids = get_json().get("ids", [])
    for order, phase_id in enumerate(ids, start=1):
        phase = Phase.query.filter_by(id=phase_id, experiment_id=experiment_id).first()
        if phase:
            phase.sort_order = order
            db.session.add(phase)
    audit("reorder_phases", None, after={"experiment_id": experiment_id, "ids": ids}, actor_id=actor.id)
    db.session.commit()
    return list_phases(experiment_id)


@bp.get("/phases/<int:phase_id>/steps")
@login_required()
def list_steps(phase_id):
    phase = _phase_or_404(phase_id)
    if not can_view_experiment(current_user(), phase.experiment_id):
        raise APIError("FORBIDDEN", "Experiment access is required.", 403)
    steps = Step.query.filter_by(phase_id=phase_id, is_deleted=False).order_by(Step.sort_order.asc()).all()
    return ok([step.to_dict() for step in steps])


@bp.post("/phases/<int:phase_id>/steps")
@login_required()
def create_step(phase_id):
    actor = current_user()
    phase = _phase_or_404(phase_id)
    if not can_manage_experiment(actor, phase.experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    data = get_json()
    require_fields(data, ["title"])
    next_order = Step.query.filter_by(phase_id=phase_id, is_deleted=False).count() + 1
    step = Step(
        phase_id=phase_id,
        title=data["title"],
        content=data.get("content", ""),
        status=data.get("status", "todo"),
        sort_order=int(data.get("sort_order", next_order)),
        creator_id=actor.id,
    )
    db.session.add(step)
    db.session.flush()
    audit("create_step", step, after=step.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(step.to_dict(), status=201)


@bp.patch("/steps/<int:step_id>")
@login_required()
def update_step(step_id):
    actor = current_user()
    step = _step_or_404(step_id)
    phase = _phase_or_404(step.phase_id)
    if not can_manage_experiment(actor, phase.experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    before = step.to_dict()
    update_model(step, get_json(), ["title", "content", "status", "sort_order"])
    db.session.add(step)
    audit("update_step", step, before=before, after=step.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(step.to_dict())


@bp.post("/steps/<int:step_id>/status")
@login_required()
def set_step_status(step_id):
    return update_step(step_id)


@bp.delete("/steps/<int:step_id>")
@login_required()
def delete_step(step_id):
    actor = current_user()
    step = _step_or_404(step_id)
    phase = _phase_or_404(step.phase_id)
    if not can_manage_experiment(actor, phase.experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    before = step.to_dict()
    step.soft_delete(actor.id, get_json().get("reason"))
    db.session.add(step)
    audit("delete_step", step, before=before, after=step.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(step.to_dict())


@bp.post("/phases/<int:phase_id>/steps/reorder")
@login_required()
def reorder_steps(phase_id):
    actor = current_user()
    phase = _phase_or_404(phase_id)
    if not can_manage_experiment(actor, phase.experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    ids = get_json().get("ids", [])
    for order, step_id in enumerate(ids, start=1):
        step = Step.query.filter_by(id=step_id, phase_id=phase_id).first()
        if step:
            step.sort_order = order
            db.session.add(step)
    audit("reorder_steps", None, after={"phase_id": phase_id, "ids": ids}, actor_id=actor.id)
    db.session.commit()
    return list_steps(phase_id)
