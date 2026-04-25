import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Pasugo API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database Settings (set in environment variables)
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "pasugo")
    
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "pasugo-secret-key-2026-aiven-migration-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 525600  # 365 days – mobile app persistent login
    REFRESH_TOKEN_EXPIRE_DAYS: int = 365
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["*"]
    
    # Upload Settings
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Cloudinary Settings
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "drw82hgul")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "919455215967269")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "hE8IC3zaav86RegKQzB2jKmOfvQ")
    CLOUDINARY_FOLDER_PREFIX: str = "pasugo"  # For organizing uploads
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Redis Settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "true").lower() == "true"
    
    # OpenRouteService (distance calculation)
    ORS_API_KEY: str = os.getenv("ORS_API_KEY", "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjcyZTc2YWMyODUwYzQ3NDNiYmJlNzU3YzNlYTYyZWQ0IiwiaCI6Im11cm11cjY0In0=")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()