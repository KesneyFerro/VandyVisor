from pydantic import PostgresDsn, field_validator, HttpUrl
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "VandyVisor"
    
    # Database
    DB_DRIVER: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    @field_validator("SQLALCHEMY_DATABASE_URI", mode="after")
    def assemble_db_connection(cls, v: Optional[str], values) -> str:
        if v:
            return v
        
        driver = values.data.get("DB_DRIVER")
        user = values.data.get("DB_USER")
        password = values.data.get("DB_PASSWORD")
        host = values.data.get("DB_HOST")
        port = values.data.get("DB_PORT")
        db = values.data.get("DB_NAME")
        
        return f"{driver}://{user}:{password}@{host}:{port}/{db}"
    
    # JWT Authentication
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Environment
    ENVIRONMENT: str
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
