from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, jsonify, request
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import CONFIGS
from .extensions import csrf, db, login_manager, migrate


def create_app(config: str | dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True, static_folder="static", template_folder="templates")

    if isinstance(config, dict):
        app.config.from_object(CONFIGS["testing"] if config.get("TESTING") else CONFIGS["development"])
        app.config.update(config)
    else:
        config_name = config or os.getenv("FLASK_ENV", "development")
        app.config.from_object(CONFIGS.get(str(config_name), CONFIGS["development"]))

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    if app.config.get("TRUST_PROXY"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.session_protection = app.config.get("SESSION_PROTECTION", "basic")

    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/") or request.path.startswith("/dash/"):
            return jsonify(error="Authentication required."), 401
        from flask import redirect, url_for
        return redirect(url_for("auth.login", next=request.full_path))

    @app.context_processor
    def inject_local_time():
        from .timeutils import local_now
        now = local_now()
        return {"now_hour": now.hour, "local_now": now}

    from .auth import bp as auth_bp
    from .pages import bp as pages_bp
    from .api import bp as api_bp
    from .admin_api import bp as admin_api_bp
    from .planning import bp as planning_bp
    from .reports import bp as reports_bp
    from .admin_transfer import bp as admin_transfer_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_api_bp)
    app.register_blueprint(planning_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_transfer_bp)

    from .dashboards import init_dash
    init_dash(app)

    from .cli import register_commands
    register_commands(app)

    @app.errorhandler(CSRFError)
    def csrf_error(error: CSRFError):
        if request.path.startswith("/api/"):
            return jsonify(error="Security token expired. Refresh and try again."), 400
        return error.description, 400

    @app.errorhandler(403)
    def forbidden(_error):
        if request.path.startswith("/api/"):
            return jsonify(error="You do not have permission to access this resource."), 403
        from flask import render_template

        return render_template("403.html"), 403

    @app.errorhandler(413)
    def too_large(_error):
        if request.path.startswith("/api/"):
            return jsonify(error="The upload is larger than the configured limit."), 413
        return "Upload too large", 413

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok"), 200

    @app.get("/readyz")
    def readyz():
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            db.session.rollback()
            app.logger.exception("Readiness database check failed")
            return jsonify(status="not_ready"), 503
        return jsonify(status="ok"), 200

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(self), geolocation=(self), microphone=(), payment=(), usb=()",
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")

        dash_inline = " 'unsafe-inline'" if request.path.startswith("/dash/") else ""
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            f"script-src 'self'{dash_inline} https://cdn.plot.ly https://unpkg.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob: https://*.tile.openstreetmap.org; "
            "connect-src 'self' https://*.tile.openstreetmap.org; "
            "worker-src 'self' blob:; "
            "frame-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self';",
        )
        if current_user.is_authenticated and response.mimetype == "text/html":
            response.headers.setdefault("Cache-Control", "private, no-cache")
        return response

    logging.basicConfig(
        level=getattr(logging, app.config["LOG_LEVEL"], logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return app
