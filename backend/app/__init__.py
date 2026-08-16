"""Factory de l'application Flask (architecture Blueprint)."""
import time
from uuid import uuid4

from flask import Flask, g, jsonify, request

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
    # Les origines sont declarees plutot qu'ouvertes : voir `ORIGINES_AUTORISEES`
    # dans la configuration pour la raison.
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["ORIGINES_AUTORISEES"]}},
        supports_credentials=True,
    )

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
    from .blueprints.assistant import assistant_bp
    from .blueprints.signalements import signalements_bp
    from .blueprints.evaluations import evaluations_bp
    from .blueprints.journal import journal_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api")
    app.register_blueprint(offers_bp, url_prefix="/api/offers")
    app.register_blueprint(applications_bp, url_prefix="/api/applications")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(profile_bp, url_prefix="/api/profile")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
    app.register_blueprint(assistant_bp, url_prefix="/api/assistant")
    app.register_blueprint(signalements_bp, url_prefix="/api/signalements")
    app.register_blueprint(evaluations_bp, url_prefix="/api/evaluations")
    app.register_blueprint(journal_bp, url_prefix="/api/journal")

    # --- Commandes CLI ---
    from .seeds import seed_command
    from .bi import creer_vues_command, export_command
    from .cli import lister_utilisateurs, reinitialiser_mot_de_passe
    from .demo import demo_command
    app.cli.add_command(seed_command)
    app.cli.add_command(lister_utilisateurs)
    app.cli.add_command(reinitialiser_mot_de_passe)
    app.cli.add_command(demo_command)
    app.cli.add_command(creer_vues_command)
    app.cli.add_command(export_command)

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

    # --- Observabilité des requêtes ---
    #
    # Chaque requête reçoit un identifiant, renvoyé dans l'en-tête
    # `X-Request-ID`. Sans lui, un utilisateur qui signale « ça a planté » ne
    # donne rien d'exploitable ; avec lui, il suffit de chercher cet
    # identifiant dans les journaux pour retrouver l'appel exact, sa durée et
    # son code de retour. Un identifiant déjà présent dans la requête est
    # conservé — c'est ce qui permettra plus tard de suivre un appel à travers
    # plusieurs services.
    @app.before_request
    def _ouvrir_trace():
        g.identifiant_requete = request.headers.get("X-Request-ID") or uuid4().hex[:12]
        g.debut_requete = time.perf_counter()

    @app.after_request
    def _fermer_trace(reponse):
        debut = g.pop("debut_requete", None)
        identifiant = g.get("identifiant_requete")
        if debut is not None and identifiant:
            duree = round((time.perf_counter() - debut) * 1000)
            reponse.headers["X-Request-ID"] = identifiant
            # Les fichiers statiques et la sonde de vie sont écartés : ils
            # noieraient les appels qui comptent sous un flot de bruit.
            if not request.path.startswith(("/static", "/api/health")):
                app.logger.info(
                    "%s %s %s %dms id=%s",
                    request.method, request.path, reponse.status_code,
                    duree, identifiant,
                )
        return reponse

    # --- Sondes ---
    @app.get("/api/health")
    def health():
        """Vivacité : le processus répond. N'interroge rien d'autre."""
        return jsonify(status="ok")

    @app.get("/api/ready")
    def ready():
        """Disponibilité : les dépendances nécessaires au service répondent.

        La distinction est celle qu'attend un orchestrateur. Un processus
        vivant mais sans base de données ne doit pas recevoir de trafic ; le
        redémarrer n'y changerait rien, alors qu'attendre, si.

        Les modèles d'intelligence artificielle sont signalés sans être
        bloquants : leur absence dégrade l'analyse, elle ne l'empêche pas.
        """
        from sqlalchemy import text

        from .services import semantique
        from .services.ml import prediction

        try:
            db.session.execute(text("SELECT 1"))
            base = True
        except Exception as exc:                       # pragma: no cover
            app.logger.warning("Base de données injoignable : %s", exc)
            base = False

        return jsonify(
            status="ready" if base else "degraded",
            dependances={
                "base_de_donnees": base,
                "modele_semantique": semantique.encoder("test") is not None,
                "modele_appris": prediction.disponible(),
            },
        ), (200 if base else 503)

    return app
