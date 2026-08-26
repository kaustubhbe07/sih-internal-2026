import os
from dotenv import load_dotenv

load_dotenv(override=True) 

class Settings:

    # Default points to Neon PostgreSQL.  Override via .env for local dev.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@ep-example-123456.us-east-2.aws.neon.tech/credential_chain?sslmode=require",
    )

    
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRY_MINUTES: int = int(os.getenv("JWT_EXPIRY_MINUTES", "60"))

    
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")

    
    # Fixed genesis value for the first record in each institution's chain.
    GENESIS_HASH: str = "0" * 64

    #chech once
    # Directory where per-institution RSA private key PEM files are saved.
    KEYS_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "keys",
    )


settings = Settings()
