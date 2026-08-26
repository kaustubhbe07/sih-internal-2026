from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.ledger.models import Base

logger = logging.getLogger(__name__)

# Use DATABASE_URL from config.py which has override=True enabled
DATABASE_URL = settings.DATABASE_URL

# SQLite needs check_same_thread=False; PostgreSQL needs connect_timeout.
if DATABASE_URL and DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
else:
    _connect_args = {"connect_timeout": 10}  # 10s TCP timeout for psycopg2

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,       # detect stale/dead connections before using them
    pool_timeout=10,          # max 10s wait for a connection from the pool
    pool_recycle=300,         # recycle connections every 5 min (Neon closes idle ones)
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create tables if they don't exist. Non-fatal on failure so the server still starts."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created / verified successfully.")
    except Exception as exc:
        logger.warning(
            "Could not create database tables on startup (DB may be temporarily "
            "unavailable). Tables will be created on first successful connection. "
            "Error: %s",
            exc,
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()