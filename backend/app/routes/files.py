from pathlib import Path

from flask import Blueprint, current_app, request, send_file

from ..extensions import db
from ..models import FileAsset, Phase, PresentationVersion, Step, StepFile, User
from ..security import can_manage_experiment, can_view_experiment, current_user, login_required
from ..utils import APIError, audit, create_step_file, get_json, ok, save_upload, validate_upload
from ..workspace import FOLDER_FILE_OWNER, FOLDER_OWNER, ROOT_FILE_OWNER

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


def _file_data(file_asset: FileAsset) -> dict:
    data = file_asset.to_dict()
    data["uploader"] = _user_summary(file_asset.uploader_id)
    return data


def _folder_data(folder: FileAsset) -> dict:
    data = folder.to_dict()
    data["name"] = folder.original_filename
    data["parent_id"] = int(folder.file_path) if folder.file_path else None
    data["creator"] = _user_summary(folder.uploader_id)
    return data


def _folder_or_404(folder_id: int) -> FileAsset:
    folder = FileAsset.query.filter_by(id=folder_id, owner_type=FOLDER_OWNER, is_deleted=False).first_or_404()
    return folder


def _folder_parent_key(folder_id: int | None) -> str:
    return str(folder_id) if folder_id else ""


def _assert_folder_in_experiment(folder_id: int | None, experiment_id: int) -> FileAsset | None:
    if not folder_id:
        return None
    folder = _folder_or_404(folder_id)
    if folder.owner_id != experiment_id:
        raise APIError("INVALID_FOLDER", "Folder does not belong to this experiment.", 422)
    return folder


def _experiment_id_for_workspace_file(asset: FileAsset) -> int:
    if asset.owner_type == ROOT_FILE_OWNER:
        return asset.owner_id
    if asset.owner_type == FOLDER_FILE_OWNER:
        folder = _folder_or_404(asset.owner_id)
        return folder.owner_id
    raise APIError("NOT_FOUND", "Resource not found.", 404)


def _collect_folder_tree(folder: FileAsset) -> list[FileAsset]:
    folders = [folder]
    children = FileAsset.query.filter_by(
        owner_type=FOLDER_OWNER,
        owner_id=folder.owner_id,
        file_path=str(folder.id),
        is_deleted=False,
    ).all()
    for child in children:
        folders.extend(_collect_folder_tree(child))
    return folders


def _workspace_breadcrumbs(folder: FileAsset | None) -> list[dict]:
    if not folder:
        return []
    folders = []
    current = folder
    while current:
        folders.append(current)
        current = FileAsset.query.get(int(current.file_path)) if current.file_path else None
    return [_folder_data(item) for item in reversed(folders)]


@bp.get("/steps/<int:step_id>/files")
@login_required()
def list_step_files(step_id):
    experiment_id = _experiment_id_from_step(step_id)
    if not can_view_experiment(current_user(), experiment_id):
        raise APIError("FORBIDDEN", "File access is required.", 403)
    files = StepFile.query.filter_by(step_id=step_id, is_deleted=False).order_by(StepFile.created_at.desc()).all()
    return ok([_file_data(item) for item in files])


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
    return ok(_file_data(step_file), status=201)


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
    return ok([_file_data(item) for item in versions])


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
    return ok(_file_data(version), status=201)


@bp.get("/experiments/<int:experiment_id>/workspace")
@login_required()
def list_experiment_workspace(experiment_id):
    actor = current_user()
    if not can_view_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment file access is required.", 403)
    folder_id = request.args.get("folder_id", type=int)
    folder = _assert_folder_in_experiment(folder_id, experiment_id)
    parent_key = _folder_parent_key(folder_id)
    folders = FileAsset.query.filter_by(
        owner_type=FOLDER_OWNER,
        owner_id=experiment_id,
        file_path=parent_key,
        is_deleted=False,
    ).order_by(FileAsset.original_filename.asc()).all()
    if folder_id:
        files_query = FileAsset.query.filter_by(owner_type=FOLDER_FILE_OWNER, owner_id=folder_id, is_deleted=False)
    else:
        files_query = FileAsset.query.filter_by(owner_type=ROOT_FILE_OWNER, owner_id=experiment_id, is_deleted=False)
    files = files_query.order_by(FileAsset.updated_at.desc()).all()
    return ok(
        {
            "current_folder": _folder_data(folder) if folder else None,
            "breadcrumbs": _workspace_breadcrumbs(folder),
            "folders": [_folder_data(item) for item in folders],
            "files": [_file_data(item) for item in files],
        }
    )


@bp.post("/experiments/<int:experiment_id>/workspace/folders")
@login_required()
def create_experiment_folder(experiment_id):
    actor = current_user()
    if not can_view_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment file access is required.", 403)
    data = get_json()
    name = (data.get("name") or "").strip()
    if not name:
        raise APIError("VALIDATION_ERROR", "Folder name is required.", 422)
    parent_id = data.get("parent_id")
    _assert_folder_in_experiment(parent_id, experiment_id)
    folder = FileAsset(
        owner_type=FOLDER_OWNER,
        owner_id=experiment_id,
        uploader_id=actor.id,
        original_filename=name,
        stored_filename="",
        file_path=_folder_parent_key(parent_id),
        file_ext="",
        mime_type="inode/directory",
        file_size=0,
    )
    db.session.add(folder)
    db.session.flush()
    audit("create_experiment_folder", folder, after=folder.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(_folder_data(folder), status=201)


@bp.patch("/experiment-workspace/folders/<int:folder_id>")
@login_required()
def update_experiment_folder(folder_id):
    actor = current_user()
    folder = _folder_or_404(folder_id)
    if not can_view_experiment(actor, folder.owner_id):
        raise APIError("FORBIDDEN", "Experiment file access is required.", 403)
    data = get_json()
    name = (data.get("name") or "").strip()
    if not name:
        raise APIError("VALIDATION_ERROR", "Folder name is required.", 422)
    before = folder.to_dict()
    folder.original_filename = name
    db.session.add(folder)
    audit("update_experiment_folder", folder, before=before, after=folder.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(_folder_data(folder))


@bp.delete("/experiment-workspace/folders/<int:folder_id>")
@login_required()
def delete_experiment_folder(folder_id):
    actor = current_user()
    folder = _folder_or_404(folder_id)
    if not can_view_experiment(actor, folder.owner_id):
        raise APIError("FORBIDDEN", "Experiment file access is required.", 403)
    folders = _collect_folder_tree(folder)
    before = {"folder_ids": [item.id for item in folders]}
    for item in folders:
        files = FileAsset.query.filter_by(owner_type=FOLDER_FILE_OWNER, owner_id=item.id, is_deleted=False).all()
        for file_asset in files:
            file_asset.soft_delete(actor.id, "Experiment folder deleted.")
            db.session.add(file_asset)
        item.soft_delete(actor.id, "Experiment folder deleted.")
        db.session.add(item)
    audit("delete_experiment_folder", folder, before=before, actor_id=actor.id)
    db.session.commit()
    return ok({"removed": folder_id})


@bp.post("/experiments/<int:experiment_id>/workspace/files")
@login_required()
def upload_experiment_workspace_file(experiment_id):
    actor = current_user()
    if not can_view_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment file access is required.", 403)
    file = request.files.get("file")
    if not file:
        raise APIError("NO_FILE", "File is required.", 422)
    folder_id = request.form.get("folder_id", type=int)
    _assert_folder_in_experiment(folder_id, experiment_id)
    meta = save_upload(file, "experiment_workspace", experiment_id)
    asset = FileAsset(
        owner_type=FOLDER_FILE_OWNER if folder_id else ROOT_FILE_OWNER,
        owner_id=folder_id or experiment_id,
        uploader_id=actor.id,
        **meta,
    )
    db.session.add(asset)
    db.session.flush()
    audit("upload_experiment_workspace_file", asset, after=asset.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(_file_data(asset), status=201)


@bp.patch("/experiment-workspace/files/<int:file_id>")
@login_required()
def rename_experiment_workspace_file(file_id):
    actor = current_user()
    asset = FileAsset.query.get_or_404(file_id)
    experiment_id = _experiment_id_for_workspace_file(asset)
    if asset.is_deleted or not can_view_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment file access is required.", 403)
    data = get_json()
    name = (data.get("name") or "").strip()
    if not name:
        raise APIError("VALIDATION_ERROR", "File name is required.", 422)
    before = asset.to_dict()
    asset.original_filename = name
    db.session.add(asset)
    audit("rename_experiment_workspace_file", asset, before=before, after=asset.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(_file_data(asset))


@bp.post("/experiment-workspace/files/<int:file_id>/replace")
@login_required()
def replace_experiment_workspace_file(file_id):
    actor = current_user()
    asset = FileAsset.query.get_or_404(file_id)
    experiment_id = _experiment_id_for_workspace_file(asset)
    if asset.is_deleted or not can_view_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment file access is required.", 403)
    file = request.files.get("file")
    if not file:
        raise APIError("NO_FILE", "File is required.", 422)
    before = asset.to_dict()
    meta = save_upload(file, "experiment_workspace", experiment_id)
    for key, value in meta.items():
        setattr(asset, key, value)
    asset.uploader_id = actor.id
    db.session.add(asset)
    audit("replace_experiment_workspace_file", asset, before=before, after=asset.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(_file_data(asset))


@bp.get("/experiment-workspace/files/<int:file_id>/download")
@login_required()
def download_experiment_workspace_file(file_id):
    actor = current_user()
    asset = FileAsset.query.get_or_404(file_id)
    experiment_id = _experiment_id_for_workspace_file(asset)
    if asset.is_deleted or not can_view_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment file access is required.", 403)
    return _safe_send(asset.file_path, asset.original_filename)


@bp.delete("/experiment-workspace/files/<int:file_id>")
@login_required()
def delete_experiment_workspace_file(file_id):
    actor = current_user()
    asset = FileAsset.query.get_or_404(file_id)
    experiment_id = _experiment_id_for_workspace_file(asset)
    if asset.is_deleted or not can_view_experiment(actor, experiment_id):
        raise APIError("FORBIDDEN", "Experiment file access is required.", 403)
    before = asset.to_dict()
    asset.soft_delete(actor.id, "Experiment workspace file deleted.")
    db.session.add(asset)
    audit("delete_experiment_workspace_file", asset, before=before, after=asset.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(_file_data(asset))


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
