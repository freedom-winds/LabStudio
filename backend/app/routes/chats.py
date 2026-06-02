from datetime import timedelta

from flask import Blueprint, request

from ..extensions import db
from ..models import Chat, ChatMember, ChatMessage, FileAsset, User, now_iso
from ..security import current_user, login_required
from ..utils import APIError, audit, create_file_asset, get_json, ok, parse_iso
from .files import _safe_send

bp = Blueprint("chats", __name__)


def _require_member(chat_id: int, user_id: int) -> ChatMember:
    member = ChatMember.query.filter_by(chat_id=chat_id, user_id=user_id).first()
    if not member:
        raise APIError("FORBIDDEN", "Chat membership is required.", 403)
    return member


def _private_chat_between(user_id: int, other_id: int) -> Chat | None:
    owned_chat_ids = [row.chat_id for row in ChatMember.query.filter_by(user_id=user_id).all()]
    if not owned_chat_ids:
        return None
    candidate_members = ChatMember.query.filter(
        ChatMember.chat_id.in_(owned_chat_ids),
        ChatMember.user_id == other_id,
    ).all()
    for member in candidate_members:
        chat = Chat.query.filter_by(id=member.chat_id, chat_type="private").first()
        if chat and ChatMember.query.filter_by(chat_id=chat.id).count() == 2:
            return chat
    return None


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


def _serialize_message(message: ChatMessage) -> dict:
    data = message.to_dict()
    data["sender"] = _user_summary(message.sender_id)
    return data


@bp.get("")
@login_required()
def list_chats():
    actor = current_user()
    rows = ChatMember.query.filter_by(user_id=actor.id).all()
    chats = []
    for row in rows:
        chat = Chat.query.get(row.chat_id)
        if not chat:
            continue
        item = chat.to_dict()
        item["unread_count"] = ChatMessage.query.filter_by(chat_id=chat.id, is_recalled=False).count()
        latest = ChatMessage.query.filter_by(chat_id=chat.id).order_by(ChatMessage.sent_at.desc()).first()
        item["latest_message"] = _serialize_message(latest) if latest else None
        item["last_activity_at"] = latest.sent_at if latest else (chat.updated_at or chat.created_at)
        chats.append(item)
    chats.sort(key=lambda item: item.get("last_activity_at") or "", reverse=True)
    return ok(chats)


@bp.post("")
@login_required()
def create_private_chat():
    actor = current_user()
    data = get_json()
    other_id = data.get("user_id")
    if not other_id:
        raise APIError("VALIDATION_ERROR", "user_id is required.", 422)
    other_id = int(other_id)
    if other_id == actor.id:
        raise APIError("INVALID_CHAT_TARGET", "Cannot create a private chat with yourself.", 422)
    other = User.query.get_or_404(other_id)
    chat = _private_chat_between(actor.id, other_id)
    if chat:
        return ok(chat.to_dict())
    chat = Chat(chat_type="private", title=data.get("title") or f"{actor.real_name} 与 {other.real_name}")
    db.session.add(chat)
    db.session.flush()
    db.session.add(ChatMember(chat_id=chat.id, user_id=actor.id))
    db.session.add(ChatMember(chat_id=chat.id, user_id=other_id))
    audit("create_chat", chat, after=chat.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(chat.to_dict(), status=201)


@bp.delete("/<int:chat_id>")
@login_required()
def delete_chat(chat_id):
    actor = current_user()
    _require_member(chat_id, actor.id)
    chat = Chat.query.get_or_404(chat_id)
    if chat.chat_type != "private" and actor.account_type != "admin":
        raise APIError("FORBIDDEN", "Only administrators can delete group chats.", 403)
    members = ChatMember.query.filter_by(chat_id=chat_id).all()
    messages = ChatMessage.query.filter_by(chat_id=chat_id).all()
    before = chat.to_dict()
    before["member_ids"] = [member.user_id for member in members]
    before["message_count"] = len(messages)
    for message in messages:
        if message.attachment_file_id:
            asset = FileAsset.query.get(message.attachment_file_id)
            if asset and not asset.is_deleted:
                asset.soft_delete(actor.id, "Chat deleted.")
                db.session.add(asset)
        db.session.delete(message)
    for member in members:
        db.session.delete(member)
    audit("delete_chat", chat, before=before, actor_id=actor.id)
    db.session.delete(chat)
    db.session.commit()
    return ok({"removed": chat_id})


@bp.get("/<int:chat_id>/messages")
@login_required()
def list_messages(chat_id):
    actor = current_user()
    member = _require_member(chat_id, actor.id)
    member.last_read_at = now_iso()
    db.session.add(member)
    messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.sent_at.asc()).limit(200).all()
    return ok([_serialize_message(item) for item in messages])


@bp.post("/<int:chat_id>/messages")
@login_required()
def send_message(chat_id):
    actor = current_user()
    _require_member(chat_id, actor.id)
    content = ""
    attachment_id = None
    message_type = "text"
    if request.files.get("file"):
        asset = create_file_asset(request.files["file"], "chat", chat_id, actor.id)
        db.session.flush()
        attachment_id = asset.id
        content = request.form.get("content", asset.original_filename)
        message_type = "file"
    else:
        data = get_json()
        content = data.get("content", "")
    if not content and not attachment_id:
        raise APIError("VALIDATION_ERROR", "Message content or file is required.", 422)
    message = ChatMessage(
        chat_id=chat_id,
        sender_id=actor.id,
        message_type=message_type,
        content=content,
        attachment_file_id=attachment_id,
    )
    db.session.add(message)
    db.session.flush()
    audit("send_chat_message", message, after=message.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(_serialize_message(message), status=201)


@bp.post("/messages/<int:message_id>/recall")
@login_required()
def recall_message(message_id):
    actor = current_user()
    message = ChatMessage.query.get_or_404(message_id)
    _require_member(message.chat_id, actor.id)
    if message.sender_id != actor.id:
        raise APIError("FORBIDDEN", "Only the sender can recall this message.", 403)
    if parse_iso(now_iso()) - parse_iso(message.sent_at) > timedelta(minutes=5):
        raise APIError("RECALL_EXPIRED", "Messages can only be recalled within 5 minutes.", 409)
    before = message.to_dict()
    message.is_recalled = True
    message.recalled_at = now_iso()
    db.session.add(message)
    audit("recall_chat_message", message, before=before, after=message.to_dict(), actor_id=actor.id)
    db.session.commit()
    return ok(message.to_dict())


@bp.get("/files/<int:file_id>/download")
@login_required()
def download_chat_file(file_id):
    actor = current_user()
    asset = FileAsset.query.get_or_404(file_id)
    if asset.owner_type != "chat":
        raise APIError("NOT_FOUND", "Resource not found.", 404)
    _require_member(asset.owner_id, actor.id)
    return _safe_send(asset.file_path, asset.original_filename)
