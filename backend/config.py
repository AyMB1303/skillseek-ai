"""Configuration par environnement (développement, test, production)."""
import os
from datetime import timedelta


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-32-characters-min!!")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://skillseek:skillseek_dev_password@localhost:5432/skillseek",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT : access court (15 min) + refresh (7 jours) - RG-02 / securite
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key-32-characters!!")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    # Uploads CV : chemin ABSOLU (send_file de Flask refuse les chemins relatifs)
    UPLOAD_FOLDER = os.path.abspath(os.getenv("UPLOAD_FOLDER", "uploads"))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 Mo max par CV

    # Origines autorisees a appeler l'API depuis un navigateur.
    #
    # « * » convenait tant que le frontend et l'API partageaient la machine du
    # developpeur. Deploye, il autoriserait n'importe quel site a interroger
    # l'API avec les identifiants de la personne connectee. La liste est donc
    # declaree, avec le poste de developpement pour valeur par defaut.
    ORIGINES_AUTORISEES = [
        origine.strip()
        for origine in os.getenv(
            "FRONTEND_ORIGIN", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origine.strip()
    ]

    # Protection contre l'essai systematique de mots de passe : au-dela du
    # seuil, le compte vise refuse les tentatives pendant une duree courte.
    SEUIL_VERROU_CONNEXION = int(os.getenv("LOGIN_MAX_ECHECS", "5"))
    DUREE_VERROU_CONNEXION = timedelta(
        minutes=int(os.getenv("LOGIN_VERROU_MINUTES", "10"))
    )


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    # Base en memoire : les tests tournent sans PostgreSQL (CI comprise)
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(BaseConfig):
    DEBUG = False


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
