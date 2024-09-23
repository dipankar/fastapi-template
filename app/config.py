from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: list = ["*"]
    
    # Email settings for magic link
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str
    
    # Google OAuth settings
    GOOGLE_CLIENT_ID: str
    
    # Apple Sign In settings
    APPLE_PUBLIC_KEY: str
    
    # Base URL for magic link
    BASE_URL: str

    # Dramatiq settings
    DRAMATIQ_BROKER: str = "redis"  # or "rabbitmq" if you prefer
    REDIS_URL: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"

settings = Settings()