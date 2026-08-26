"""
Issuance service — orchestrates crypto + ledger for credential issuance.

Handles both single and bulk issuance. Validates dynamic custom fields
against the institution's field_schema.
"""

from datetime import date
from sqlalchemy.orm import Session

from app.ledger.models import Institution, CredentialRecord
from app.ledger import repository as repo
from app.crypto.hashing import compute_credential_hash, get_prev_hash
from app.crypto.signing import sign_hash
from app.core.config import settings


def validate_custom_fields(institution: Institution, custom_fields: dict | None) -> list[str]:
    """
    Validate custom_fields against the institution's field_schema.

    Returns a list of error messages (empty if valid).
    """
    errors = []
    schema = institution.field_schema or []

    if not schema and custom_fields:
        errors.append("This institution has no custom fields defined.")
        return errors

    if not schema:
        return errors  # no schema, no custom fields — fine

    schema_map = {}
    for field in schema:
        if isinstance(field, dict) and "name" in field:
            schema_map[field["name"]] = field
        elif isinstance(field, str):
            schema_map[field] = {"name": field, "required": False}
        # Ignore completely malformed entries

    # Check required fields are present
    for field_name, field_def in schema_map.items():
        if field_def.get("required", False):
            if not custom_fields or field_name not in custom_fields:
                errors.append(f"Missing required custom field: {field_name}")

    # Check no unknown fields
    if custom_fields:
        for key in custom_fields:
            if key not in schema_map:
                errors.append(f"Unknown custom field: {key}")

    return errors


def issue_single(
    db: Session,
    institution: Institution,
    student_name: str,
    roll_no: str,
    degree: str,
    cgpa: str | None,
    issue_date: date,
    prev_hash: str,
    custom_fields: dict | None = None,
) -> CredentialRecord:
    """
    Core logic to hash, sign, and build a single CredentialRecord.
    """
    record_hash = compute_credential_hash(
        student_name=student_name,
        roll_no=roll_no,
        degree=degree,
        institution_id=str(institution.id),
        issue_date=str(issue_date),
        prev_hash=prev_hash,
        custom_fields=custom_fields,
    )

    signature = sign_hash(record_hash, institution.private_key_path)
    
    credential = CredentialRecord(
        institution_id=institution.id,
        student_name=student_name,
        roll_no=roll_no,
        degree=degree,
        cgpa=cgpa,
        issue_date=issue_date,
        custom_fields=custom_fields,
        prev_hash=prev_hash,
        record_hash=record_hash,
        signature=signature,
        qr_payload=None,
    )
    repo.insert_credential(db, credential)

    # Set QR payload now that we have the credential ID.
    credential.qr_payload = f"{settings.BASE_URL}/verify/{credential.id}"
    return credential


def issue_bulk(
    db: Session,
    institution: Institution,
    rows: list[dict],
) -> list[CredentialRecord]:
    """
    Issue multiple credentials in order, chaining each to the previous.
    Caller is responsible for validation before calling this.
    """
    hash_list = repo.get_chain_hashes(db, institution.id)
    prev_hash = get_prev_hash(hash_list)

    results = []
    for data in rows:
        cred = issue_single(
            db=db,
            institution=institution,
            student_name=data["student_name"],
            roll_no=data["roll_no"],
            degree=data["degree"],
            cgpa=data.get("cgpa"),
            issue_date=data["issue_date"],
            prev_hash=prev_hash,
            custom_fields=data.get("custom_fields"),
        )
        prev_hash = cred.record_hash
        results.append(cred)

    return results
