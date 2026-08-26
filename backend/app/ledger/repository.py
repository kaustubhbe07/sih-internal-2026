from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ledger.models import CredentialRecord, RevocationEvent, Institution

def _ensure_uuid(val):
    if isinstance(val, str):
        try:
            return uuid.UUID(val)
        except ValueError:
            return None
    return val

class InstituteRepository:
    def __init__(self, session: Session):
        self._session = session

    def add_institute(self, institute: Institution) -> Institution:
        self._session.add(institute)
        self._session.commit()
        self._session.refresh(institute)
        return institute
        
    def get_institute_by_id(self, institute_id: str) -> Institution | None:
        u_id = _ensure_uuid(institute_id)
        if not u_id: return None
        stmt = select(Institution).where(Institution.id == u_id)
        return self._session.scalars(stmt).first()

    def get_institution_by_email(self, email: str) -> Institution | None:
        stmt = select(Institution).where(Institution.email == email)
        return self._session.scalars(stmt).first()

class CredentialRepository:
    def __init__(self, session: Session):
        self._session = session

    def add(self, record: CredentialRecord) -> CredentialRecord:
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def get_latest(self) -> CredentialRecord | None:
        stmt = select(CredentialRecord).order_by(CredentialRecord.id.desc()).limit(1)
        return self._session.scalars(stmt).first()

    def get_by_credential_id(self, credential_id: str) -> CredentialRecord | None:
        u_id = _ensure_uuid(credential_id)
        if not u_id: return None
        stmt = select(CredentialRecord).where(CredentialRecord.id == u_id)
        return self._session.scalars(stmt).first()

    def get_by_hash(self, record_hash: str) -> CredentialRecord | None:
        stmt = select(CredentialRecord).where(CredentialRecord.record_hash == record_hash)
        return self._session.scalars(stmt).first()

    def list_all(self, institute_id) -> list[CredentialRecord]:
        u_id = _ensure_uuid(institute_id)
        if not u_id: return []
        stmt = select(CredentialRecord).where(CredentialRecord.institution_id == u_id).order_by(CredentialRecord.created_at.asc())
        return list(self._session.scalars(stmt).all())

    def exists_for_student(self, institute_id: str, roll_no: str, degree: str) -> bool:
        u_id = _ensure_uuid(institute_id)
        if not u_id: return False
        stmt = select(CredentialRecord).where(
            CredentialRecord.institution_id == u_id,
            CredentialRecord.roll_no == roll_no,
            CredentialRecord.degree == degree
        ).limit(1)
        return self._session.scalars(stmt).first() is not None

    def insert(self, record: CredentialRecord) -> CredentialRecord:
        """Add a credential record and flush (so the ID is assigned)."""
        self._session.add(record)
        self._session.flush()
        self._session.refresh(record)
        return record

    def get_chain_hashes(self, institute_id: str) -> list[str]:
        """Return all record_hash values for an institution's credential chain, in order."""
        u_id = _ensure_uuid(institute_id)
        if not u_id: return []
        stmt = (
            select(CredentialRecord.record_hash)
            .where(CredentialRecord.institution_id == u_id)
            .order_by(CredentialRecord.created_at.asc())
        )
        return list(self._session.scalars(stmt).all())

    def get_chain(self, institute_id: str) -> list[CredentialRecord]:
        """Return the full credential chain for an institution, oldest first."""
        u_id = _ensure_uuid(institute_id)
        if not u_id: return []
        stmt = (
            select(CredentialRecord)
            .where(CredentialRecord.institution_id == u_id)
            .order_by(CredentialRecord.created_at.asc())
        )
        return list(self._session.scalars(stmt).all())


class RevocationRepository:
    def __init__(self, session: Session):
        self._session = session

    def add(self, event: RevocationEvent) -> RevocationEvent:
        self._session.add(event)
        self._session.commit()
        self._session.refresh(event)
        return event

    def get_by_credential_id(self, credential_id: str) -> RevocationEvent | None:
        u_id = _ensure_uuid(credential_id)
        if not u_id: return None
        stmt = select(RevocationEvent).where(RevocationEvent.credential_id == u_id)
        return self._session.scalars(stmt).first()