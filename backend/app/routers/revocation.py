"""
Revocation router — revoke credentials and check revocation status.

POST /revocations              — revoke a credential
GET  /credentials/{id}/revocation-status       — check if a credential is revoked
"""

import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ledger.db import get_db
from app.ledger.models import RevocationEvent
from app.ledger.repository import InstituteRepository, CredentialRepository, RevocationRepository
from app.core.security import get_current_institution
from app.crypto.hashing import compute_revocation_hash, get_prev_hash
from app.crypto.signing import sign_hash
from app.schemas.revocation import (
    RevokeRequest,
    RevocationEventOut,
    RevocationStatusResponse,
)

router = APIRouter(tags=["revocation"])


@router.post("/revocations", response_model=RevocationEventOut, status_code=201)
def revoke_credential(
    body: RevokeRequest,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_current_institution),
):
    """
    Revoke a credential. Revocations are append-only.
    The original credential is not modified.
    """
    try:
        cred_uuid = _uuid.UUID(body.credential_id)
        inst_uuid = _uuid.UUID(institution_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format")

    cred_repo = CredentialRepository(db)
    inst_repo = InstituteRepository(db)
    rev_repo = RevocationRepository(db)

    # a. Fetch credential
    credential = cred_repo.get_by_credential_id(str(cred_uuid))
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    # b. Confirm ownership
    if str(credential.institution_id) != str(inst_uuid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke a credential issued by another institution",
        )

    # c. Check if already revoked
    if rev_repo.get_by_credential_id(str(cred_uuid)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credential already revoked",
        )

    # Load institution for private key
    institution = inst_repo.get_institute_by_id(str(inst_uuid))
    if not institution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")

    # d. Compute prev_hash from revocation chain
    stmt = select(RevocationEvent.record_hash).where(
        RevocationEvent.institution_id == inst_uuid
    ).order_by(RevocationEvent.id.asc())
    hash_list = list(db.scalars(stmt).all())
    prev_hash = get_prev_hash(hash_list)

    now_ts = datetime.now(timezone.utc)
    timestamp_str = now_ts.isoformat()

    # e. Compute record_hash
    record_hash = compute_revocation_hash(
        credential_id=body.credential_id,
        reason=body.reason,
        institution_id=institution_id,
        timestamp=timestamp_str,
        prev_hash=prev_hash,
    )

    # f. Sign
    signature = sign_hash(record_hash, institution.private_key_path)

    # g. Insert
    revocation = RevocationEvent(
        credential_id=cred_uuid,
        institution_id=inst_uuid,
        reason=body.reason,
        prev_hash=prev_hash,
        record_hash=record_hash,
        signature=signature,
        created_at=now_ts,
    )
    rev_repo.add(revocation)

    return RevocationEventOut(
        id=str(revocation.id),
        credential_id=str(revocation.credential_id),
        institution_id=str(revocation.institution_id),
        reason=revocation.reason,
        prev_hash=revocation.prev_hash,
        record_hash=revocation.record_hash,
        signature=revocation.signature,
        created_at=revocation.created_at,
    )


@router.get("/credentials/{credential_id}/revocation-status", response_model=RevocationStatusResponse)
def get_revocation_status(credential_id: str, db: Session = Depends(get_db)):
    """Public endpoint to check if a credential is revoked."""
    try:
        cred_uuid = _uuid.UUID(credential_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    cred_repo = CredentialRepository(db)
    rev_repo = RevocationRepository(db)

    credential = cred_repo.get_by_credential_id(str(cred_uuid))
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    revocation = rev_repo.get_by_credential_id(str(cred_uuid))
    if revocation:
        return RevocationStatusResponse(
            revoked=True,
            reason=revocation.reason,
            revoked_at=revocation.created_at,
        )
    return RevocationStatusResponse(revoked=False)