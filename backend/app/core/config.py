import os
from dataclasses import dataclass


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    secret_key: str = os.getenv("SECRET_KEY", "development-only-change-me")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./campus_exchange.db")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "Admin123!" if os.getenv("APP_ENV", "development") == "development" else "")
    sms_provider: str = os.getenv("SMS_PROVIDER", "console")
    sms_code_expire_seconds: int = int(os.getenv("SMS_CODE_EXPIRE_SECONDS", "300"))
    sms_send_interval_seconds: int = int(os.getenv("SMS_SEND_INTERVAL_SECONDS", "60"))
    demo_features_enabled: bool = env_flag(
        "DEMO_FEATURES_ENABLED",
        os.getenv("APP_ENV", "development") == "development",
    )
    email_provider: str = os.getenv("EMAIL_PROVIDER", "console")
    email_code_expire_seconds: int = int(os.getenv("EMAIL_CODE_EXPIRE_SECONDS", "600"))
    email_send_interval_seconds: int = int(os.getenv("EMAIL_SEND_INTERVAL_SECONDS", "60"))
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")
    smtp_security: str = os.getenv("SMTP_SECURITY", "starttls")
    frontend_origins: list[str] = tuple(
        origin.strip()
        for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    )

    @property
    def public_upload_dir(self) -> str:
        return os.path.join(self.upload_dir, "public")

    @property
    def private_upload_dir(self) -> str:
        return os.path.join(self.upload_dir, "private")


settings = Settings()
