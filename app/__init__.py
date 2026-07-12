"""
LearnMate AI – Application Factory
"""
import logging
import os
from flask import Flask
from app.config import get_config
from app.extensions import db, login_manager, bcrypt, csrf, migrate


def create_app(config_class=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # Logging
    logging.basicConfig(
        level=logging.DEBUG if app.config.get("DEBUG") else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.tutor import tutor_bp
    from app.routes.roadmap import roadmap_bp
    from app.routes.quiz import quiz_bp
    from app.routes.progress import progress_bp
    from app.routes.resources import resources_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(tutor_bp)
    app.register_blueprint(roadmap_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(resources_bp)

    # Create tables
    with app.app_context():
        db.create_all()

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template("errors/500.html"), 500

    # Custom Jinja2 filters
    import json as _json
    @app.template_filter('fromjson')
    def fromjson_filter(value):
        try:
            return _json.loads(value)
        except Exception:
            return []

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from datetime import datetime
        return {
            "app_name": app.config.get("APP_NAME", "LearnMate AI"),
            "current_user": current_user,
            "now": datetime.utcnow(),
            "zip": zip,
        }

    return app
