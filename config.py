from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test.db"
    API_ENDPOINT_BASE_URL: str =  "http://localhost:8000"
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

@lru_cache()
def get_settings():
    return Settings()

# Export settings instance
settings = get_settings()
