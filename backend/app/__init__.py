"""Factory de l'application Flask (architecture Blueprint)."""
from flask import Flask, jsonify

from config import CONFIGS
from .extensions import db, migrate, jwt, bcrypt, cors


def create_app(env: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(CONFIGS[env])

    # --- Extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # --- Modèles (importés pour qu'Alembic les voie) ---
    from . import models  # noqa: F401

    # --- Blueprints ---
    from .blueprints.auth import auth_bp
    from .blueprints.users import users_bp
    from .blueprints.offers import offers_bp
    from .blueprints.applications import applications_bp
    from .blueprints.dashboard import dashboard_bp
    from .blueprints.profile import profile_bp
    from .blueprints.notifications import notifications_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api")
    app.register_blueprint(offers_bp, url_prefix="/api/offers")
    app.register_blueprint(applications_bp, url_prefix="/api/applications")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(profile_bp, url_prefix="/api/profile")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")

    # --- Commande CLI de seed ---
    from .seeds import seed_command
    app.cli.add_command(seed_command)

    # --- Callbacks JWT : blacklist ---
    from .models.token_blocklist import TokenBlocklist

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        return db.session.query(
            TokenBlocklist.query.filter_by(jti=jti).exists()
        ).scalar()

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify(error="Session révoquée, veuillez vous reconnecter."), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify(error="Token expiré."), 401

    @jwt.unauthorized_loader
    def missing_token_callback(reason):
        return jsonify(error="Authentification requise."), 401

    # --- Gestion centralisée des erreurs ---
    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Ressource introuvable."), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify(error="Erreur interne du serveur."), 500

    # --- Healthcheck ---
    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    return app
