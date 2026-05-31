from .extensions import db
from .models import FileAsset
from .utils import audit

FOLDER_OWNER = "experiment_workspace_folder"
ROOT_FILE_OWNER = "experiment_workspace_file_root"
FOLDER_FILE_OWNER = "experiment_workspace_file"
DEFAULT_EXPERIMENT_FOLDERS = ("论文", "PPT")


def ensure_default_experiment_folders(experiment_id: int, actor_id: int) -> None:
    existing_names = {
        row.original_filename
        for row in FileAsset.query.filter_by(
            owner_type=FOLDER_OWNER,
            owner_id=experiment_id,
            file_path="",
            is_deleted=False,
        ).all()
    }
    for name in DEFAULT_EXPERIMENT_FOLDERS:
        if name in existing_names:
            continue
        folder = FileAsset(
            owner_type=FOLDER_OWNER,
            owner_id=experiment_id,
            uploader_id=actor_id,
            original_filename=name,
            stored_filename="",
            file_path="",
            file_ext="",
            mime_type="inode/directory",
            file_size=0,
        )
        db.session.add(folder)
        db.session.flush()
        audit("create_default_experiment_folder", folder, after=folder.to_dict(), actor_id=actor_id)
