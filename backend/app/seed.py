from __future__ import annotations

from .extensions import db
from .models import User


def seed() -> None:
    """Create the minimal initial platform state."""
    admin = User.query.filter_by(username="00000000").first()
    if not admin:
        admin = User(
            username="00000000",
            real_name="系统管理员",
            gender="男",
            account_type="admin",
            is_first_login=False,
            status="active",
        )
        admin.set_password("Admin1234!")
        db.session.add(admin)
    else:
        admin.real_name = "系统管理员"
        admin.gender = "男"
        admin.account_type = "admin"
        admin.status = "active"
        admin.is_first_login = False
    db.session.commit()
