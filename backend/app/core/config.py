import os
from dotenv import load_dotenv

load_dotenv(override=True) 

class Settings:

    DATABASE_URL: str | None = os.getenv("DATABASE_URL")

    
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRY_MINUTES: int = int(os.getenv("JWT_EXPIRY_MINUTES", "60"))

    
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")

    
    # Fixed genesis value for the first record in each institution's chain.
    GENESIS_HASH: str = "0" * 64




settings = Settings()
