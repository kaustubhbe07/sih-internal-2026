"""
Credential Verification — FastAPI application entry point.

Registers all routers and exposes the ASGI app object that uvicorn serves.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import issuance as issuance_router
from app.routers import verification as verification_router
from app.routers import revocation as revocation_router
from app.routers import auth as auth_router
from app.ledger.db import init_db


app = FastAPI(
    title="Credential Verification",
    description=(
        "Blockchain-inspired tamper-proof academic credential verification "
        "(SIH 2026 — PS-03 prototype)"
    ),
    version="1.0.0",
)

# ── CORS Middleware ──────────────────────────────────────────────────────
frontend_url = os.getenv("FRONTEND_URL", "*")
origins = [origin.strip() for origin in frontend_url.split(",")] if frontend_url != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ─────────────────────────────────────────────────────
app.include_router(auth_router.router, prefix="/auth")
app.include_router(issuance_router.router)
app.include_router(verification_router.router)
app.include_router(revocation_router.router)


@app.get("/", tags=["health"])
def health_check():
    """Simple liveness probe."""
    return {"status": "ok", "service": "credential-verification"}


@app.on_event("startup")
def on_startup():
    """Create all database tables if they don't exist."""
    init_db()
