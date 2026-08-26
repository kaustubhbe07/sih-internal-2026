import hashlib
import json

# FIELD_ORDER = [
#     "credential_id",
#     "student_id",
#     "student_name",
#     "course_name",
#     "grade",
#     "issue_date",
# ]

GENESIS_HASH = "0" * 64

# def serialize_record(record:dict)-> str:
#     ordered={field:record[field] for field in FIELD_ORDER}
#     return json.dumps(
#         ordered,
#         sort_keys=False,
#         separators=(",",":"),
#         ensure_ascii=True
#     )

def compute_hash(fields:dict, prev_hash:str)->str:
    # payload=serialize_record(record)+prev_hash
    # return hashlib.sha256(payload.encode("utf-8")).hexdigest()
    sorted_fields=json.dumps(fields, sort_keys=True,separators=(",",":"),ensure_ascii=True)
    payload=sorted_fields+prev_hash
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def compute_credential_hash(
    student_name: str,
    roll_no: str,
    degree: str,
    institution_id: str,
    issue_date: str,
    prev_hash: str,
    custom_fields: dict | None = None,
) -> str:
    
    fields = {
        "student_name": student_name,
        "roll_no": roll_no,
        "degree": degree,
        "institution_id": institution_id,
        "issue_date": issue_date,
    }
    if custom_fields:
        # Prefix custom fields to avoid collision with standard fields.
        for k, v in custom_fields.items():
            fields[f"custom_{k}"] = str(v)
    return compute_hash(fields, prev_hash)

def compute_revocation_hash(
    credential_id: str,
    reason: str,
    institution_id: str,
    timestamp: str,
    prev_hash: str,
) -> str:
    
    fields = {
        "credential_id": credential_id,
        "reason": reason,
        "institution_id": institution_id,
        "timestamp": timestamp,
    }
    return compute_hash(fields, prev_hash)


def get_prev_hash(existing_hashes: list[str]) -> str:
    
    if not existing_hashes:
        return GENESIS_HASH
    return existing_hashes[-1]


def is_genesis(prev_hash: str) -> bool:
    return prev_hash == GENESIS_HASH