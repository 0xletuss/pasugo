import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Pasugo API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database Settings - Aiven
    DB_HOST: str = os.getenv("DB_HOST", "pasugodb-bayadpasugo.g.aivencloud.com")
    DB_PORT: int = int(os.getenv("DB_PORT", "17013"))
    DB_USER: str = os.getenv("DB_USER", "avnadmin")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "za$Snb4@&p8SiHe8A4{W]#WBr7c77li)")
    DB_NAME: str = os.getenv("DB_NAME", "defaultdb")
    
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