from __future__ import annotations

import json
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class TimestampMixin:
    created_at = db.Column(db.String(32), default=now_iso, nullable=False)
    updated_at = db.Column(db.String(32), default=now_iso, onupdate=now_iso, nullable=False)


class SoftDeleteMixin:
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_by = db.Column(db.Integer, nullable=True)
    deleted_at = db.Column(db.String(32), nullable=True)
    delete_reason = db.Column(db.Text, nullable=True)

    def soft_delete(self, user_id: int | None, reason: str | None = None) -> None:
        self.is_deleted = True
        self.deleted_by = user_id
        self.deleted_at = now_iso()
        self.delete_reason = reason or ""


class SerializerMixin:
    __hidden__ = set()

    def to_dict(self) -> dict:
        data = {}
        for column in self.__table__.columns:
            if column.name in self.__hidden__:
                continue
            data[column.name] = getattr(self, column.name)
        return data


class User(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "users"
    __hidden__ = {"password_hash"}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(8), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    real_name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)
    is_first_login = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    last_login_at = db.Column(db.String(32), nullable=True)
    deleted_by = db.Column(db.Integer, nullable=True)
    deleted_at = db.Column(db.String(32), nullable=True)
    delete_reason = db.Column(db.Text, nullable=True)

    def to_dict(self) -> dict:
        data = super().to_dict()
        avatar = FileAsset.query.filter_by(
            owner_type="user_avatar",
            owner_id=self.id,
            is_deleted=False,
        ).order_by(FileAsset.updated_at.desc()).first()
        data["avatar_url"] = f"/api/users/{self.id}/avatar?v={avatar.id}" if avatar else ""
        return data

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_deleted(self) -> bool:
        return self.status == "deleted"

    @is_deleted.setter
    def is_deleted(self, value: bool) -> None:
        if value:
            self.status = "deleted"

    def soft_delete(self, user_id: int | None, reason: str | None = None) -> None:
        self.status = "deleted"
        self.deleted_by = user_id
        self.deleted_at = now_iso()
        self.delete_reason = reason or ""


class AuthToken(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "auth_tokens"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(96), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    expires_at = db.Column(db.String(32), nullable=False)
    revoked_at = db.Column(db.String(32), nullable=True)


class Year(db.Model, TimestampMixin, SoftDeleteMixin, SerializerMixin):
    __tablename__ = "years"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    year_number = db.Column(db.Integer, unique=True, nullable=False)
    status = db.Column(db.String(20), default="open", nullable=False)


class YearMember(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "year_members"
    __table_args__ = (db.UniqueConstraint("year_id", "user_id", name="uq_year_member"),)

    id = db.Column(db.Integer, primary_key=True)
    year_id = db.Column(db.Integer, db.ForeignKey("years.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    roles = db.Column(db.Text, default="[]", nullable=False)

    @property
    def role_list(self) -> list[str]:
        try:
            return json.loads(self.roles or "[]")
        except json.JSONDecodeError:
            return []

    @role_list.setter
    def role_list(self, values: list[str]) -> None:
        self.roles = json.dumps(values, ensure_ascii=False)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["roles"] = self.role_list
        return data


class Topic(db.Model, TimestampMixin, SoftDeleteMixin, SerializerMixin):
    __tablename__ = "topics"

    id = db.Column(db.Integer, primary_key=True)
    year_id = db.Column(db.Integer, db.ForeignKey("years.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class Team(db.Model, TimestampMixin, SoftDeleteMixin, SerializerMixin):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    year_id = db.Column(db.Integer, db.ForeignKey("years.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    final_competition_level = db.Column(db.String(20), nullable=True)
    final_award_level = db.Column(db.String(20), nullable=True)
    award_description = db.Column(db.Text, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class TeamMember(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "team_members"
    __table_args__ = (db.UniqueConstraint("team_id", "user_id", name="uq_team_member"),)

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    role = db.Column(db.String(20), default="member", nullable=False)


class TeamTopic(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "team_topics"
    __table_args__ = (db.UniqueConstraint("team_id", "topic_id", name="uq_team_topic"),)

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False, index=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class TeamExperiment(db.Model, TimestampMixin, SoftDeleteMixin, SerializerMixin):
    __tablename__ = "team_experiments"
    __table_args__ = (db.UniqueConstraint("team_id", "topic_id", name="uq_team_topic_experiment"),)

    id = db.Column(db.Integer, primary_key=True)
    year_id = db.Column(db.Integer, db.ForeignKey("years.id"), nullable=False, index=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False, index=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False)
    status = db.Column(db.String(20), default="working", nullable=False)


class ExperimentMember(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "experiment_members"
    __table_args__ = (db.UniqueConstraint("experiment_id", "user_id", name="uq_experiment_member"),)

    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey("team_experiments.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    role = db.Column(db.String(20), default="participant", nullable=False)


class Phase(db.Model, TimestampMixin, SoftDeleteMixin, SerializerMixin):
    __tablename__ = "phases"

    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey("team_experiments.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    goal = db.Column(db.Text, default="", nullable=False)
    expected_start_date = db.Column(db.String(20), nullable=True)
    expected_end_date = db.Column(db.String(20), nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class Step(db.Model, TimestampMixin, SoftDeleteMixin, SerializerMixin):
    __tablename__ = "steps"

    id = db.Column(db.Integer, primary_key=True)
    phase_id = db.Column(db.Integer, db.ForeignKey("phases.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    content = db.Column(db.Text, default="", nullable=False)
    status = db.Column(db.String(20), default="todo", nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class StepFile(db.Model, TimestampMixin, SoftDeleteMixin, SerializerMixin):
    __tablename__ = "step_files"

    id = db.Column(db.Integer, primary_key=True)
    step_id = db.Column(db.Integer, db.ForeignKey("steps.id"), nullable=False, index=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_ext = db.Column(db.String(20), nullable=False)
    mime_type = db.Column(db.String(120), nullable=True)
    file_size = db.Column(db.Integer, nullable=False)
    file_category = db.Column(db.String(20), default="document", nullable=False)


class FileAsset(db.Model, TimestampMixin, SoftDeleteMixin, SerializerMixin):
    __tablename__ = "file_assets"

    id = db.Column(db.Integer, primary_key=True)
    owner_type = db.Column(db.String(40), nullable=False)
    owner_id = db.Column(db.Integer, nullable=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_ext = db.Column(db.String(20), nullable=False)
    mime_type = db.Column(db.String(120), nullable=True)
    file_size = db.Column(db.Integer, nullable=False)


class Proposal(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "proposals"
    __table_args__ = (db.UniqueConstraint("experiment_id", "submitter_id", name="uq_proposal_owner"),)

    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey("team_experiments.id"), nullable=False, index=True)
    submitter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    file_id = db.Column(db.Integer, db.ForeignKey("file_assets.id"), nullable=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)


class PresentationVersion(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "presentation_versions"

    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey("team_experiments.id"), nullable=False, index=True)
    version_no = db.Column(db.Integer, nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    change_note = db.Column(db.Text, default="", nullable=False)
    is_current = db.Column(db.Boolean, default=False, nullable=False)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)


class Reservation(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    year_id = db.Column(db.Integer, db.ForeignKey("years.id"), nullable=True, index=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey("team_experiments.id"), nullable=True)
    start_time = db.Column(db.String(32), nullable=False)
    end_time = db.Column(db.String(32), nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    participants_note = db.Column(db.Text, default="", nullable=False)
    final_status = db.Column(db.String(20), default="pending", nullable=False)
    duty_teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)


class ReservationApproval(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "reservation_approvals"
    __table_args__ = (db.UniqueConstraint("reservation_id", "teacher_id", name="uq_reservation_teacher"),)

    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey("reservations.id"), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)
    comment = db.Column(db.Text, default="", nullable=False)


class Chat(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "chats"

    id = db.Column(db.Integer, primary_key=True)
    chat_type = db.Column(db.String(20), nullable=False)
    year_id = db.Column(db.Integer, db.ForeignKey("years.id"), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey("team_experiments.id"), nullable=True)
    title = db.Column(db.String(160), nullable=False)


class ChatMember(db.Model, TimestampMixin, SerializerMixin):
    __tablename__ = "chat_members"
    __table_args__ = (db.UniqueConstraint("chat_id", "user_id", name="uq_chat_member"),)

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chats.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    last_read_at = db.Column(db.String(32), nullable=True)


class ChatMessage(db.Model, SerializerMixin):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chats.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message_type = db.Column(db.String(20), default="text", nullable=False)
    content = db.Column(db.Text, default="", nullable=False)
    attachment_file_id = db.Column(db.Integer, db.ForeignKey("file_assets.id"), nullable=True)
    is_recalled = db.Column(db.Boolean, default=False, nullable=False)
    sent_at = db.Column(db.String(32), default=now_iso, nullable=False)
    recalled_at = db.Column(db.String(32), nullable=True)


class Announcement(db.Model, TimestampMixin, SoftDeleteMixin, SerializerMixin):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    scope = db.Column(db.String(20), nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    title = db.Column(db.String(180), nullable=False)
    content = db.Column(db.Text, nullable=False)
    publisher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)


class ToolboxItem(db.Model, TimestampMixin, SoftDeleteMixin, SerializerMixin):
    __tablename__ = "toolbox_items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    version = db.Column(db.String(40), nullable=False)
    file_path = db.Column(db.String(500), nullable=True)
    file_size = db.Column(db.Integer, default=0, nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)


class HonorMember(db.Model, TimestampMixin, SoftDeleteMixin, SerializerMixin):
    __tablename__ = "honor_members"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    year_id = db.Column(db.Integer, db.ForeignKey("years.id"), nullable=True)
    image_path = db.Column(db.String(500), nullable=True)
    linked_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_visible = db.Column(db.Boolean, default=True, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class Notification(db.Model, SerializerMixin):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    notification_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    content = db.Column(db.Text, default="", nullable=False)
    related_object_type = db.Column(db.String(50), nullable=True)
    related_object_id = db.Column(db.Integer, nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.String(32), default=now_iso, nullable=False)


class AuditLog(db.Model, SerializerMixin):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    action_type = db.Column(db.String(80), nullable=False)
    object_type = db.Column(db.String(80), nullable=False)
    object_id = db.Column(db.Integer, nullable=True)
    before_data = db.Column(db.Text, nullable=True)
    after_data = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(80), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.String(32), default=now_iso, nullable=False)
