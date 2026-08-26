"""
Pydantic schemas for revocation endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RevokeRequest(BaseModel):
    """Body for POST /revocations."""
    credential_id: str
    reason: str


class RevocationEventOut(BaseModel):
    """Response shape for a created revocation event."""
    id: str
    credential_id: str
    institution_id: str
    reason: str
    prev_hash: str
    record_hash: str
    signature: str
    created_at: datetime


class RevocationStatusResponse(BaseModel):
    """Response shape for GET /credentials/{id}/revocation-status."""
    revoked: bool
    reason: Optional[str] = None
    revoked_at: Optional[datetime] = None
