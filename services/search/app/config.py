from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    chroma_host: str = "chromadb"
    chroma_port: int = 8000
    jwt_secret: str
    jwt_algorithm: str = "HS256"


settings = Settings()
