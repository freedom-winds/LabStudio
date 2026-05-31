from .announcements import bp as announcements_bp
from .audit_logs import bp as audit_logs_bp
from .auth import bp as auth_bp
from .chats import bp as chats_bp
from .dashboard import bp as dashboard_bp
from .experiments import bp as experiments_bp
from .files import bp as files_bp
from .honors import bp as honors_bp
from .notifications import bp as notifications_bp
from .planning import bp as planning_bp
from .proposals import bp as proposals_bp
from .public import bp as public_bp
from .reservations import bp as reservations_bp
from .toolbox import bp as toolbox_bp
from .topics import bp as topics_bp
from .users import bp as users_bp
from .years import bp as years_bp
from .teams import bp as teams_bp


def register_routes(app):
    app.register_blueprint(public_bp, url_prefix="/api/public")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(years_bp, url_prefix="/api/years")
    app.register_blueprint(topics_bp, url_prefix="/api/topics")
    app.register_blueprint(teams_bp, url_prefix="/api/teams")
    app.register_blueprint(experiments_bp, url_prefix="/api/experiments")
    app.register_blueprint(planning_bp, url_prefix="/api")
    app.register_blueprint(files_bp, url_prefix="/api")
    app.register_blueprint(proposals_bp, url_prefix="/api")
    app.register_blueprint(reservations_bp, url_prefix="/api/reservations")
    app.register_blueprint(chats_bp, url_prefix="/api/chats")
    app.register_blueprint(announcements_bp, url_prefix="/api/announcements")
    app.register_blueprint(toolbox_bp, url_prefix="/api/toolbox")
    app.register_blueprint(honors_bp, url_prefix="/api/honor-members")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
    app.register_blueprint(audit_logs_bp, url_prefix="/api/audit-logs")
