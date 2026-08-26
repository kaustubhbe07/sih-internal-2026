"""
Verification router — public endpoints for credential verification.

GET  /verify/{credential_id}  — verify a credential by ID
"""

import uuid as _uuid

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.ledger.db import get_db
from app.services.verification_service import verify_credential
from app.schemas.credential import VerifyResponse

router = APIRouter(tags=["verification"])


@router.get("/verify/{credential_id}", response_model=VerifyResponse)
def verify(credential_id: str, db: Session = Depends(get_db)):
    """Public endpoint to verify a credential's authenticity."""
    try:
        cred_uuid = _uuid.UUID(credential_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    return verify_credential(db, cred_uuid)
