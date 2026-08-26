from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ledger.db import get_db
from app.services import auth_service
from app.schemas.credential import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse
)

router = APIRouter(tags=["auth"])

@router.post("/register", response_model=RegisterResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new institution. 
    This creates the institution record and generates its RSA keypair.
    """
    return auth_service.register_institution(db, req)

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate an institution and return a JWT access token.
    """
    return auth_service.login_institution(db, req)
