from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Long & Short Quant"
    DATABASE_URL: str = "postgresql://user:password@localhost/dbname"
    REDIS_URL: str = "redis://localhost:6379"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "your_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    REPORTS_STORAGE_DIR: str = "generated_reports"


    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
