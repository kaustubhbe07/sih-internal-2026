from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, Column, JSON, ForeignKey, Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Institution(Base):

    __tablename__ = "institutions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    public_key = Column(Text, nullable=False)         
    private_key_path = Column(Text, nullable=False)     
    field_schema = Column(JSON, nullable=True)         
    created_at = Column(DateTime, default=datetime.utcnow)


class CredentialRecord(Base):
   
    __tablename__ = "credential_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(
        UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False
    )
    student_name = Column(Text, nullable=False)
    roll_no = Column(Text, nullable=False)
    degree = Column(Text, nullable=False)
    cgpa = Column(Text, nullable=True)
    issue_date = Column(Date, nullable=False)
    custom_fields = Column(JSON, nullable=True)         
    prev_hash = Column(Text, nullable=False)
    record_hash = Column(Text, nullable=False)
    signature = Column(Text, nullable=False)            
    qr_payload = Column(Text, nullable=True)            
    created_at = Column(DateTime, default=_utc_now)

class RevocationEvent(Base):
    
    __tablename__ = "revocation_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    credential_id = Column(
        UUID(as_uuid=True), ForeignKey("credential_records.id"), nullable=False
    )
    institution_id = Column(
        UUID(as_uuid=True), ForeignKey("institutions.id"), nullable=False
    )
    reason = Column(Text, nullable=False)
    prev_hash = Column(Text, nullable=False)
    record_hash = Column(Text, nullable=False)
    signature = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utc_now)   
    revoked_at= Column(DateTime, default=_utc_now)