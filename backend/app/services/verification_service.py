"""
Verification service — signature check → hash check → chain walk → revocation check.

Decoupled from HTTP: this module returns data objects, not HTTP responses.
"""

import uuid as _uuid
from sqlalchemy.orm import Session

from app.ledger.models import Institution, CredentialRecord
from app.ledger import repository as repo
from app.crypto.hashing import compute_credential_hash
from app.crypto.signing import verify_signature
from app.schemas.credential import (
    VerifyResponse,
    CredentialSummary,
    RevocationInfo,
)


def verify_credential(db: Session, cred_uuid: _uuid.UUID) -> VerifyResponse:
    """
    Core verification logic — performs four independent checks:
      1. Hash validity — recompute record_hash from stored fields
      2. Chain integrity — walk from genesis to this credential
      3. Signature — verify Ed25519 signature with institution's public key
      4. Revocation — check if a revocation event exists
    """
    # ─── Fetch the credential ────────────────────────────────────────
    cred_repo = repo.CredentialRepository(db)
    credential = cred_repo.get_by_credential_id(cred_uuid)
    if not credential:
        return VerifyResponse(status="NOT_FOUND")

    # ─── Fetch the issuing institution ───────────────────────────────
    inst_repo = repo.InstituteRepository(db)
    institution = inst_repo.get_institute_by_id(credential.institution_id)

    # ─── CHECK 1: Hash validity ──────────────────────────────────────
    recomputed_hash = compute_credential_hash(
        student_name=credential.student_name,
        roll_no=credential.roll_no,
        degree=credential.degree,
        institution_id=str(credential.institution_id),
        issue_date=str(credential.issue_date),
        prev_hash=credential.prev_hash,
        custom_fields=credential.custom_fields,
    )
    hash_valid = recomputed_hash == credential.record_hash

    # ─── CHECK 2: Chain integrity (genesis → this credential) ────────
    chain_intact = True
    full_chain = cred_repo.get_chain(credential.institution_id)

    expected_prev_hash = "0" * 64
    for record in full_chain:
        recomputed = compute_credential_hash(
            student_name=record.student_name,
            roll_no=record.roll_no,
            degree=record.degree,
            institution_id=str(record.institution_id),
            issue_date=str(record.issue_date),
            prev_hash=record.prev_hash,
            custom_fields=record.custom_fields,
        )

        if record.prev_hash != expected_prev_hash:
            chain_intact = False
        if recomputed != record.record_hash:
            chain_intact = False

        if str(record.id) == str(credential.id):
            break

        expected_prev_hash = recomputed

    # ─── CHECK 3: Ed25519 signature ──────────────────────────────────
    signature_valid = False
    if institution:
        signature_valid = verify_signature(
            record_hash=credential.record_hash,
            signature_hex=credential.signature,
            public_key_hex=institution.public_key,
        )

    # ─── CHECK 4: Revocation status ──────────────────────────────────
    rev_repo = repo.RevocationRepository(db)
    revocation_event = rev_repo.get_by_credential_id(credential.id)

    revocation_info = None
    if revocation_event:
        revocation_info = RevocationInfo(
            reason=revocation_event.reason,
            revoked_at=revocation_event.created_at,
        )

    # ─── Determine final status ──────────────────────────────────────
    if not hash_valid or not chain_intact:
        final_status = "TAMPERED"
    elif revocation_event:
        final_status = "REVOKED"
    else:
        final_status = "VALID"

    # ─── Build credential summary ────────────────────────────────────
    summary = CredentialSummary(
        id=str(credential.id),
        student_name=credential.student_name,
        degree=credential.degree,
        roll_no=credential.roll_no,
        cgpa=credential.cgpa,
        issue_date=credential.issue_date,
        institution_name=institution.name if institution else "Unknown",
        custom_fields=credential.custom_fields,
    )

    return VerifyResponse(
        status=final_status,
        credential=summary,
        hash_valid=hash_valid,
        chain_intact=chain_intact,
        signature_valid=signature_valid,
        revocation=revocation_info,
    )
