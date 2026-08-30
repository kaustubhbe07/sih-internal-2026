import os
import time
import json
import base64
import hashlib
import hmac
import uuid

from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.ledger.repository import InstituteRepository
from app.ledger.models import Institution
from app.crypto.signing import generate_keypair
from app.schemas.credential import (
    RegisterRequest, 
    RegisterResponse, 
    LoginRequest, 
    LoginResponse
)

# Standard prototype secret
SECRET_KEY = os.getenv("SECRET_KEY", "sih2026-super-secret-key")


# ── Password Hashing (Zero-dependency PBKDF2) ───────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2 HMAC SHA256."""
    salt = os.urandom(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    # Store as base64(salt + hash)
    return base64.b64encode(salt + pwdhash).decode('ascii')


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify a plain password against the stored hash."""
    try:
        decoded = base64.b64decode(stored_hash.encode('ascii'))
        salt = decoded[:16]
        stored_pwdhash = decoded[16:]
        pwdhash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(pwdhash, stored_pwdhash)
    except Exception:
        return False


# ── Minimal JWT Implementation (Zero-dependency) ─────────────────────────

def create_jwt(institution_id: str) -> str:
    """Create a minimal JWT token for authentication."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": institution_id,
        "exp": int(time.time()) + (24 * 3600)  # 24 hours expiry
    }
    
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    
    signature = hmac.new(
        SECRET_KEY.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256
    ).digest()
    
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_jwt(token: str) -> str:
    """Verify the minimal JWT token and return the subject (institution_id)."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
            
        header_b64, payload_b64, sig_b64 = parts
        
        # Verify signature
        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            raise ValueError("Invalid signature")
            
        # Verify expiration
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "==").decode())
        if payload.get("exp", 0) < time.time():
            raise ValueError("Token expired")
            
        return payload.get("sub")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
            )

# ── Core Auth Services ───────────────────────────────────────────────────

def register_institution(db: Session, req: RegisterRequest) -> RegisterResponse:
    """Register a new institution, generating its Ed25519 keypair."""
    inst_repo = InstituteRepository(db)
    
    # 1. Check if email exists
    existing = inst_repo.get_institution_by_email(req.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered."
        )
        
    # 2. Hash password
    hashed_pwd = hash_password(req.password)
    
    # 3. Generate Institution ID and Ed25519 Keypair
    new_id = uuid.uuid4()
    public_key_pem, private_key_path = generate_keypair(str(new_id))
    
    # 4. Save to database
    new_inst = Institution(
        id=new_id,
        name=req.name,
        email=req.email,
        password_hash=hashed_pwd,
        public_key=public_key_pem,
        private_key_path=private_key_path,
        field_schema=req.field_schema
    )
    
    # The new add_institute method handles db.add(), db.commit(), and db.refresh()
    new_inst = inst_repo.add_institute(new_inst)
    
    return RegisterResponse(
        id=str(new_inst.id),
        name=new_inst.name,
        email=new_inst.email,
        public_key=new_inst.public_key,
        field_schema=new_inst.field_schema
    )


from app.core.security import create_access_token

def login_institution(db: Session, req: LoginRequest) -> LoginResponse:
    """Authenticate an institution and return a JWT."""
    inst_repo = InstituteRepository(db)
    inst = inst_repo.get_institution_by_email(req.email)
    
    if not inst or not verify_password(req.password, inst.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid email or password."
        )
        
    token = create_access_token(str(inst.id))
    return LoginResponse(
        access_token=token,
        institution_id=str(inst.id),
        institution_name=inst.name
    )