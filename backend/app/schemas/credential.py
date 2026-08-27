from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel

"""
Pydantic schemas for credential and authentication endpoints.

Request/response shapes for:
    POST /auth/register, POST /auth/login
    POST /credentials, POST /credentials/bulk
    GET  /credentials/mine
    GET  /verify/{credential_id}
    POST /verify/upload-scan
"""

# ── Auth schemas ─────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Body for POST /auth/register."""
    name: str
    email: str
    password: str
    field_schema: list[dict] | None = None  # custom field definitions


class RegisterResponse(BaseModel):
    """Returned on successful registration. Never includes private key."""
    id: str
    name: str
    email: str
    public_key: str
    field_schema: list[dict] | None = None


class LoginRequest(BaseModel):
    """Body for POST /auth/login."""
    email: str
    password: str


class LoginResponse(BaseModel):
    """Returned on successful login."""
    access_token: str
    token_type: str = "bearer"
    institution_id: str
    institution_name: str


# ── Issue endpoint ───────────────────────────────────────────────────────

class IssueRequest(BaseModel):
    """Body for POST /credentials."""
    student_name: str
    roll_no: str
    degree: str
    cgpa: Optional[str] = None
    issue_date: date
    custom_fields: dict | None = None  # institution-defined extra fields


class BulkIssueResult(BaseModel):
    row_number: int
    credential_id: str
    record_hash: str


class BulkIssueResponse(BaseModel):
    total_issued: int
    results: list[BulkIssueResult]


class CredentialOut(BaseModel):
    """
    Full credential record returned after issuance and in listings.
    Includes all hash-chain and signature fields.
    """
    id: str
    institution_id: str
    student_name: str
    roll_no: str
    degree: str
    cgpa: Optional[str] = None
    issue_date: date
    custom_fields: dict | None = None
    prev_hash: str
    record_hash: str
    signature: str
    qr_payload: Optional[str] = None
    created_at: Optional[datetime] = None
    revoked: bool = False


# ── Verify endpoint ─────────────────────────────────────────────────────

class RevocationInfo(BaseModel):
    """Revocation details included when status is REVOKED."""
    reason: str
    revoked_at: datetime


class CredentialSummary(BaseModel):
    """Subset of credential fields shown to public verifiers."""
    id: str
    student_name: str
    degree: str
    roll_no: str
    cgpa: Optional[str] = None
    issue_date: date
    institution_name: str
    custom_fields: dict | None = None


class VerifyResponse(BaseModel):
    status: str  # "VALID", "TAMPERED", "REVOKED", "NOT_FOUND"
    credential: CredentialSummary | None = None
    hash_valid: bool | None = None
    chain_intact: bool | None = None
    signature_valid: bool | None = None
    revocation: RevocationInfo | None = None


class OCRVerifyResponse(BaseModel):
    status: str  # "VALID", "TAMPERED", "REVOKED", "SUSPICIOUS"
    extracted_fields: dict
    match_confidence: float | None = None
    matched_credential: CredentialSummary | None = None
    hash_valid: bool | None = None
    chain_intact: bool | None = None
    signature_valid: bool | None = None
