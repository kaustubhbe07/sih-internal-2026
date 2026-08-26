import uuid as _uuid
import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File
from sqlalchemy.orm import Session

from app.ledger.db import get_db
from app.ledger.repository import InstituteRepository, CredentialRepository, RevocationRepository, get_chain_hashes
from app.core.security import get_current_institution
from app.crypto.hashing import get_prev_hash
from app.services.issuance_service import issue_single, issue_bulk, validate_custom_fields
from app.services.qr_service import generate_qr, generate_certificate_pdf
from app.schemas.credential import (
    IssueRequest,
    CredentialOut,
    BulkIssueResponse,
    BulkIssueResult,
)

router = APIRouter(tags=["credentials"])





# ── Issuance endpoints ──────────────────────────────────────────────────

@router.post("/credentials", response_model=CredentialOut, status_code=201)
def issue_credential(
    body: IssueRequest,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_current_institution),
):
    """Issue a single academic credential."""
    inst_repo = InstituteRepository(db)
    cred_repo = CredentialRepository(db)
    
    institution = inst_repo.get_institute_by_id(institution_id)
    if not institution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found.")

    # Validate custom fields against schema
    errors = validate_custom_fields(institution, body.custom_fields)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    hash_list = get_chain_hashes(db, institution.id)
    prev_hash = get_prev_hash(hash_list)

    credential = issue_single(
        db=db,
        institution=institution,
        student_name=body.student_name,
        roll_no=body.roll_no,
        degree=body.degree,
        cgpa=body.cgpa,
        issue_date=body.issue_date,
        prev_hash=prev_hash,
        custom_fields=body.custom_fields,
    )

    db.commit()
    db.refresh(credential)

    return _credential_to_out(credential, db)


@router.post("/credentials/bulk", response_model=BulkIssueResponse, status_code=201)
def bulk_issue_credentials(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_current_institution),
):
    """Bulk issue credentials from a CSV file."""
    inst_repo = InstituteRepository(db)
    institution = inst_repo.get_institute_by_id(institution_id)
    
    if not institution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found.")

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Must be a CSV file")

    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    # Validation phase
    rows = []
    errors = []

    custom_field_names = []
    if institution.field_schema:
        for f in institution.field_schema:
            if isinstance(f, dict) and "name" in f:
                custom_field_names.append(f["name"])
            elif isinstance(f, str):
                custom_field_names.append(f)

    for i, row in enumerate(reader, start=2):
        missing = []
        for col in ["student_name", "roll_no", "degree", "issue_date"]:
            if col not in row or not row[col].strip():
                missing.append(col)

        # Ensure required custom fields are present
        for field in (institution.field_schema or []):
            req = False
            fname = None
            if isinstance(field, dict) and "name" in field:
                req = field.get("required", False)
                fname = field["name"]
            elif isinstance(field, str):
                req = False
                fname = field
            
            if req and fname and (fname not in row or not row[fname].strip()):
                missing.append(fname)

        if missing:
            errors.append(f"Row {i}: Missing required columns: {', '.join(missing)}")
            continue

        try:
            parsed_date = datetime.strptime(row["issue_date"].strip(), "%Y-%m-%d").date()
        except ValueError:
            errors.append(f"Row {i}: issue_date must be YYYY-MM-DD")
            continue

        custom_fields = {}
        for cname in custom_field_names:
            if cname in row and row[cname].strip():
                custom_fields[cname] = row[cname].strip()

        rows.append({
            "row_number": i,
            "student_name": row["student_name"].strip(),
            "roll_no": row["roll_no"].strip(),
            "degree": row["degree"].strip(),
            "cgpa": row.get("cgpa", "").strip() or None,
            "issue_date": parsed_date,
            "custom_fields": custom_fields if custom_fields else None,
        })

    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})
    if not rows:
        raise HTTPException(status_code=400, detail="CSV is empty")

    credentials = issue_bulk(db, institution, rows)

    db.commit()
    return BulkIssueResponse(
        total_issued=len(credentials),
        results=[
            BulkIssueResult(
                row_number=rows[i]["row_number"],
                credential_id=str(cred.id),
                record_hash=cred.record_hash,
            )
            for i, cred in enumerate(credentials)
        ],
    )


@router.get("/credentials/mine", response_model=list[CredentialOut])
def list_my_credentials(
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_current_institution),
):
    """Return all credentials issued by the current institution, oldest first."""
    cred_repo = CredentialRepository(db)
    rows = cred_repo.list_all(institution_id)
    return [_credential_to_out(c, db) for c in rows]


@router.get("/credentials/{credential_id}/qr", response_class=Response)
def get_qr_code(credential_id: str, db: Session = Depends(get_db)):
    """Public endpoint to generate and return a QR code PNG."""
    cred_repo = CredentialRepository(db)
    
    try:
        _uuid.UUID(credential_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    credential = cred_repo.get_by_credential_id(credential_id)
    if not credential or not credential.qr_payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    qr_bytes = generate_qr(credential.qr_payload)
    return Response(content=qr_bytes, media_type="image/png")


@router.get("/credentials/{credential_id}/certificate", response_class=Response)
def get_certificate_pdf(credential_id: str, db: Session = Depends(get_db)):
    """Public endpoint to generate and return a PDF certificate."""
    cred_repo = CredentialRepository(db)
    inst_repo = InstituteRepository(db)
    
    try:
        _uuid.UUID(credential_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    credential = cred_repo.get_by_credential_id(credential_id)
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    institution = inst_repo.get_institute_by_id(str(credential.institution_id))
    if not institution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")

    pdf_bytes = generate_certificate_pdf(credential, institution.name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=certificate_{credential_id}.pdf"},
    )


# ── Helper ───────────────────────────────────────────────────────────────

def _credential_to_out(c, db: Session) -> CredentialOut:
    rev_repo = RevocationRepository(db)
    
    revocation_event = rev_repo.get_by_credential_id(str(c.id))
    revoked = bool(revocation_event)
    
    return CredentialOut(
        id=str(c.id),
        institution_id=str(c.institution_id),
        student_name=c.student_name,
        roll_no=c.roll_no,
        degree=c.degree,
        cgpa=c.cgpa,
        issue_date=c.issue_date,
        custom_fields=c.custom_fields,
        prev_hash=c.prev_hash,
        record_hash=c.record_hash,
        signature=c.signature,
        qr_payload=c.qr_payload,
        created_at=c.created_at,
        revoked=revoked,
    )