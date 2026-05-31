from flask import Blueprint, request

from ..extensions import db
from ..models import FileAsset, Proposal, User
from ..security import can_manage_experiment, can_view_experiment, current_user, login_required
from ..utils import APIError, audit, create_file_asset, get_json, ok
from .files import _safe_send

bp = Blueprint("proposals", __name__)


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
    }


def _proposal_data(proposal: Proposal) -> dict:
    data = proposal.to_dict()
    data["submitter"] = _user_summary(proposal.submitter_id)
    return data


@bp.get("/experiments/<int:experiment_id>/proposals")
@login_required()
def list_proposals(experiment_id):
    actor = current_user()
    if not can_view_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment access is required.", 403)
    query = Proposal.query.filter_by(experiment_id=experiment_id)
    if not can_manage_experiment(actor, experiment_id):
        query = query.filter_by(submitter_id=actor.id)
    return ok([_proposal_data(item) for item in query.order_by(Proposal.updated_at.desc()).all()])


@bp.post("/experiments/<int:experiment_id>/proposals")
@login_required()
def submit_proposal(experiment_id):
    actor = current_user()
    if not can_view_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment access is required.", 403)
    data = request.form if request.form else get_json()
    title = data.get("title") or "开题报告"
    proposal = Proposal.query.filter_by(experiment_id=experiment_id, submitter_id=actor.id).first()
    if not proposal:
        proposal = Proposal(experiment_id=experiment_id, submitter_id=actor.id, title=title)
    before = proposal.to_dict() if proposal.id else None
    proposal.title = title
    proposal.description = data.get("description", "")
    file = request.files.get("file")
    if file:
        asset = create_file_asset(file, "proposals", experiment_id, actor.id)
        db.session.flush()
        proposal.file_id = asset.id
    db.session.add(proposal)
    db.session.flush()
    audit("submit_proposal", proposal, before=before, after=proposal.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(_proposal_data(proposal), status=201 if before is None else 200)


@bp.get("/proposals/<int:proposal_id>/download")
@login_required()
def download_proposal(proposal_id):
    actor = current_user()
    proposal = Proposal.query.get_or_404(proposal_id)
    if not (can_manage_experiment(actor, proposal.experiment_id) or proposal.submitter_id == actor.id):
        raise APIError("FORBIDDEN", "Proposal access is required.", 403)
    if not proposal.file_id:
        raise APIError("NO_FILE", "Proposal has no file.", 404)
    asset = FileAsset.query.get_or_404(proposal.file_id)
    return _safe_send(asset.file_path, asset.original_filename)


@bp.delete("/proposals/<int:proposal_id>")
@login_required()
def delete_proposal(proposal_id):
    actor = current_user()
    proposal = Proposal.query.get_or_404(proposal_id)
    if not (can_manage_experiment(actor, proposal.experiment_id) or proposal.submitter_id == actor.id):
        raise APIError("FORBIDDEN", "Proposal delete permission is required.", 403)
    before = proposal.to_dict()
    if proposal.file_id:
        asset = FileAsset.query.get(proposal.file_id)
        if asset and not asset.is_deleted:
            asset.soft_delete(actor.id, "Proposal deleted.")
            db.session.add(asset)
    audit("delete_proposal", proposal, before=before, actor_id=actor.id)
    db.session.delete(proposal)
    db.session.commit()
    return ok({"removed": proposal_id})
