from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INCIDENT_LEDGER_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Demo guard
    DEMO_ONLY: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/incident_ledger"

    # OIDC (Microsoft Entra)
    OIDC_ISSUER: str = ""
    OIDC_AUDIENCE: str = ""
    OIDC_JWKS_URI: str = ""

    # Demo / local auth
    MOCK_AUTH: bool = False

    # Allowed center codes in demo environment
    ALLOWED_CENTER_CODES: list[str] = ["DEMO-MGLC-01"]

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:8081", "http://localhost:19006"]

    # Logging
    LOG_LEVEL: str = "INFO"

    # Google Cloud / Vertex AI
    GCP_PROJECT_ID: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Email (demo: console logging only)
    EMAIL_DEMO_DOMAIN: str = "demo.incident-ledger.dev"


settings = Settings()
