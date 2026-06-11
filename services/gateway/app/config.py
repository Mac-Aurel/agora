from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    auth_service_url: str = "http://auth:8000"
    boards_service_url: str = "http://boards:8000"
    content_service_url: str = "http://content:8000"
    search_service_url: str = "http://search:8000"
    discovery_service_url: str = "http://discovery:8000"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    redis_url: str = "redis://redis:6379"
    rate_limit_max_requests: int = 100
    rate_limit_window_seconds: int = 60


settings = Settings()
