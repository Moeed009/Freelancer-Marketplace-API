from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Freelancer Marketplace API"
    ENVIRONMENT: str = "development"  
    PORT: int = 8000

   
    DATABASE_URL: str = ""

    
    SUPABASE_URL: str = ""              
    SUPABASE_ANON_KEY: str = ""         
    SUPABASE_SERVICE_ROLE_KEY: str = "" 
    SUPABASE_JWT_SECRET: str = ""       
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str  
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

   
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
   
    NOTIFICATION_EMAIL_BACKEND: str = "supabase"
    NOTIFICATION_SMS_BACKEND: str = "console"
    SUPABASE_FUNCTIONS_URL: str

    NOTIFICATION_EMAIL_FUNCTION: str = ""

    SMS_PROVIDER_URL: str = ""
    SMS_PROVIDER_TOKEN: str = ""
    SMS_PROVIDER_SENDER: str = ""

    NOTIFICATION_PROVIDER_TIMEOUT: float = 10.0
    NOTIFICATION_MAX_ATTEMPTS: int = 3
    NOTIFICATION_RETRY_BACKOFF_SECONDS: int = 30
    NOTIFICATION_WORKER_ENABLED: bool = True
    NOTIFICATION_WORKER_INTERVAL_SECONDS: float = 5.0
    NOTIFICATION_WORKER_BATCH_SIZE: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()