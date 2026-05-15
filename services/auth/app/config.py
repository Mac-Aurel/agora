from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Auth service configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7


settings = Settings()
