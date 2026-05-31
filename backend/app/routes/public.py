from flask import Blueprint

from ..models import HonorMember
from ..utils import ok

bp = Blueprint("public", __name__)


@bp.get("/health")
def health():
    return ok({"status": "ok", "name": "Lexy Lab"})


@bp.get("/honor-members")
def public_honors():
    items = (
        HonorMember.query.filter_by(is_deleted=False, is_visible=True)
        .order_by(HonorMember.sort_order.asc(), HonorMember.created_at.desc())
        .all()
    )
    return ok([item.to_dict() for item in items])
