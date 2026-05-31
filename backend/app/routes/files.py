from pathlib import Path

from flask import Blueprint, current_app, request, send_file

from ..extensions import db
from ..models import Phase, PresentationVersion, Step, StepFile
from ..security import can_manage_experiment, can_view_experiment, current_user, login_required
from ..utils import APIError, audit, create_step_file, ok, save_upload, validate_upload

bp = Blueprint("files", __name__)


def _experiment_id_from_step(step_id: int) -> int:
    step = Step.query.get_or_404(step_id)
    phase = Phase.query.get_or_404(step.phase_id)
    return phase.experiment_id


def _safe_send(path: str, download_name: str):
    root = Path(current_app.config["UPLOAD_ROOT"]).resolve()
    resolved = Path(path).resolve()
    if root not in resolved.parents and resolved != root:
        raise APIError("INVALID_PATH", "Invalid file path.", 403)
    if not resolved.exists():
        raise APIError("FILE_NOT_FOUND", "File not found.", 404)
    return send_file(resolved, as_attachment=True, download_name=download_name)


@bp.get("/steps/<int:step_id>/files")
@login_required()
def list_step_files(step_id):
    experiment_id = _experiment_id_from_step(step_id)
    if not can_view_experiment(current_user(), experiment_id):
        raise APIError("FORBIDDEN", "File access is required.", 403)
    files = StepFile.query.filter_by(step_id=step_id, is_deleted=False).order_by(StepFile.created_at.desc()).all()
    return ok([item.to_dict() for item in files])


@bp.post("/steps/<int:step_id>/files")
@login_required()
def upload_step_file(step_id):
    actor = current_user()
    experiment_id = _experiment_id_from_step(step_id)
    if not can_view_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment access is required.", 403)
    file = request.files.get("file")
    if not file:
        raise APIError("NO_FILE", "File is required.", 422)
    category = request.form.get("file_category")
    step_file = create_step_file(file, step_id=step_id, uploader_id=actor.id, category=category)
    db.session.flush()
    audit("upload_step_file", step_file, after=step_file.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(step_file.to_dict(), status=201)


@bp.get("/step-files/<int:file_id>/download")
@login_required()
def download_step_file(file_id):
    actor = current_user()
    step_file = StepFile.query.get_or_404(file_id)
    experiment_id = _experiment_id_from_step(step_file.step_id)
    if step_file.is_deleted or not can_view_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "File access is required.", 403)
    return _safe_send(step_file.file_path, step_file.original_filename)


@bp.delete("/step-files/<int:file_id>")
@login_required()
def delete_step_file(file_id):
    actor = current_user()
    step_file = StepFile.query.get_or_404(file_id)
    experiment_id = _experiment_id_from_step(step_file.step_id)
    if not (can_manage_experiment(actor, experiment_id) or step_file.uploader_id == actor.id):
        raise APIError("FORBIDDEN", "File delete permission is required.", 403)
    before = step_file.to_dict()
    step_file.soft_delete(actor.id, "")
    db.session.add(step_file)
    audit("delete_step_file", step_file, before=before, after=step_file.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(step_file.to_dict())


@bp.get("/experiments/<int:experiment_id>/presentations")
@login_required()
def list_presentations(experiment_id):
    if not can_view_experiment(current_user(), experiment_id):
        raise APIError("FORBIDDEN", "Experiment access is required.", 403)
    query = PresentationVersion.query.filter_by(experiment_id=experiment_id)
    if not can_manage_experiment(current_user(), experiment_id):
        query = query.filter_by(is_hidden=False)
    versions = query.order_by(PresentationVersion.is_current.desc(), PresentationVersion.version_no.desc()).all()
    return ok([item.to_dict() for item in versions])


@bp.post("/experiments/<int:experiment_id>/presentations")
@login_required()
def upload_presentation(experiment_id):
    actor = current_user()
    if not can_view_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment access is required.", 403)
    file = request.files.get("file")
    if not file:
        raise APIError("NO_FILE", "File is required.", 422)
    validate_upload(file, category="ppt")
    meta = save_upload(file, "presentations", experiment_id)
    next_no = PresentationVersion.query.filter_by(experiment_id=experiment_id).count() + 1
    for current in PresentationVersion.query.filter_by(experiment_id=experiment_id, is_current=True).all():
        current.is_current = False
    version = PresentationVersion(
        experiment_id=experiment_id,
        version_no=next_no,
        uploader_id=actor.id,
        original_filename=meta["original_filename"],
        stored_filename=meta["stored_filename"],
        file_path=meta["file_path"],
        file_size=meta["file_size"],
        change_note=request.form.get("change_note", ""),
        is_current=True,
    )
    db.session.add(version)
    db.session.flush()
    audit("upload_presentation", version, after=version.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(version.to_dict(), status=201)


@bp.get("/presentations/<int:version_id>/download")
@login_required()
def download_presentation(version_id):
    actor = current_user()
    version = PresentationVersion.query.get_or_404(version_id)
    if version.is_hidden and not can_manage_experiment(actor, version.experiment_id):
        raise APIError("FORBIDDEN", "Presentation access is required.", 403)
    if not can_view_experiment(actor, version.experiment_id):
        raise APIError("FORBIDDEN", "Presentation access is required.", 403)
    return _safe_send(version.file_path, version.original_filename)


@bp.post("/presentations/<int:version_id>/current")
@login_required()
def set_current_presentation(version_id):
    actor = current_user()
    version = PresentationVersion.query.get_or_404(version_id)
    if not can_manage_experiment(actor, version.experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    for current in PresentationVersion.query.filter_by(experiment_id=version.experiment_id).all():
        current.is_current = current.id == version.id
        db.session.add(current)
    audit("set_current_presentation", version, after=version.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(version.to_dict())


@bp.post("/presentations/<int:version_id>/hide")
@login_required()
def hide_presentation(version_id):
    actor = current_user()
    version = PresentationVersion.query.get_or_404(version_id)
    if not can_manage_experiment(actor, version.experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    before = version.to_dict()
    version.is_hidden = True
    if version.is_current:
        version.is_current = False
        replacement = (
            PresentationVersion.query.filter(
                PresentationVersion.experiment_id == version.experiment_id,
                PresentationVersion.id != version.id,
                PresentationVersion.is_hidden.is_(False),
            )
            .order_by(PresentationVersion.version_no.desc())
            .first()
        )
        if replacement:
            replacement.is_current = True
    db.session.add(version)
    audit("hide_presentation", version, before=before, after=version.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(version.to_dict())


@bp.delete("/presentations/<int:version_id>")
@login_required()
def delete_presentation(version_id):
    actor = current_user()
    version = PresentationVersion.query.get_or_404(version_id)
    if not can_manage_experiment(actor, version.experiment_id):
        raise APIError("FORBIDDEN", "Experiment management permission is required.", 403)
    before = version.to_dict()
    version.is_hidden = True
    if version.is_current:
        version.is_current = False
        replacement = (
            PresentationVersion.query.filter(
                PresentationVersion.experiment_id == version.experiment_id,
                PresentationVersion.id != version.id,
                PresentationVersion.is_hidden.is_(False),
            )
            .order_by(PresentationVersion.version_no.desc())
            .first()
        )
        if replacement:
            replacement.is_current = True
    db.session.add(version)
    audit("delete_presentation", version, before=before, after=version.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(version.to_dict())
