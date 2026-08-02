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
