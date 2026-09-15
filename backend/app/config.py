from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./wallet.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    platform_url: str = "http://127.0.0.1:8081"
    platform_admin_key: str = "change-me-admin-key"
    platform_api_key: str = ""
    webhook_secret: str = ""

    app_name: str = "Wallet Demo"
    cors_origins: list[str] = ["*"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
