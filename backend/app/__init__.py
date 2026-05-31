from pathlib import Path

from flask import Flask, request, send_from_directory
from flask_cors import CORS

from .config import Config
from .extensions import db
from .utils import APIError, fail


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    Path(app.config["UPLOAD_ROOT"]).mkdir(parents=True, exist_ok=True)
    Path(__file__).resolve().parents[1].joinpath("data").mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    from . import models  # noqa: F401
    from .routes import register_routes

    register_routes(app)

    @app.errorhandler(APIError)
    def handle_api_error(error):
        return fail(error.code, error.message, error.status_code)

    @app.errorhandler(404)
    def handle_404(_error):
        frontend_dist = Path(app.config["FRONTEND_DIST"])
        is_api_path = request.path == "/api" or request.path.startswith("/api/")
        if request.method == "GET" and not is_api_path and frontend_dist.joinpath("index.html").is_file():
            requested = request.path.lstrip("/")
            if requested:
                asset = frontend_dist.joinpath(requested)
                if asset.is_file():
                    return send_from_directory(frontend_dist, requested)
            return send_from_directory(frontend_dist, "index.html")
        return fail("NOT_FOUND", "Resource not found.", 404)

    @app.errorhandler(500)
    def handle_500(error):
        app.logger.exception(error)
        return fail("INTERNAL_ERROR", "Internal server error.", 500)

    @app.cli.command("init-db")
    def init_db_command():
        from .seed import seed

        db.drop_all()
        db.create_all()
        seed()
        print("Database initialized with seed data.")

    return app
