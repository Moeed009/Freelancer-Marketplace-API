
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

   
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

   
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
