"""
Unit tests for app/crypto/hashing.py.

Run with: pytest app/tests/test_hashing.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crypto.hashing import compute_hash, is_genesis, GENESIS_HASH, compute_credential_hash

SAMPLE_RECORD = {
    "student_name": "Aarav Sharma",
    "roll_no": "1001",
    "degree": "B.Tech Computer Science",
    "institution_id": "inst-iit-demo",
    "issue_date": "2026-08-23",
}


def test_hash_is_deterministic():
    """Same record + same prev_hash must always produce the same hash."""
    h1 = compute_hash(SAMPLE_RECORD, GENESIS_HASH)
    h2 = compute_hash(SAMPLE_RECORD, GENESIS_HASH)
    assert h1 == h2


def test_hash_changes_on_any_field_edit():
    """Editing a single field must change the hash -- the core tamper-evidence claim."""
    original_hash = compute_hash(SAMPLE_RECORD, GENESIS_HASH)

    tampered = dict(SAMPLE_RECORD)
    tampered["degree"] = "B.Tech Computer Science (Honours)"
    tampered_hash = compute_hash(tampered, GENESIS_HASH)

    assert original_hash != tampered_hash


def test_hash_changes_if_prev_hash_changes():
    """The same record chained after a different prior record must hash differently."""
    h_after_genesis = compute_hash(SAMPLE_RECORD, GENESIS_HASH)
    h_after_other = compute_hash(SAMPLE_RECORD, "a" * 64)
    assert h_after_genesis != h_after_other


def test_hash_is_64_char_hex():
    h = compute_hash(SAMPLE_RECORD, GENESIS_HASH)
    assert len(h) == 64
    int(h, 16)  # raises ValueError if not valid hex


def test_missing_field_raises_type_error():
    """Python enforces required arguments in compute_credential_hash."""
    try:
        # missing student_name and degree
        compute_credential_hash(
            roll_no="1001",
            institution_id="inst-iit-demo",
            issue_date="2026-08-23",
            prev_hash=GENESIS_HASH
        )
        assert False, "expected TypeError for missing positional arguments"
    except TypeError:
        pass


def test_is_genesis_helper():
    assert is_genesis(GENESIS_HASH) is True
    assert is_genesis("a" * 64) is False


def test_hash_field_order_is_fixed():
    """Two dicts with the same data in different key order must hash identically."""
    reordered = {
        "issue_date": SAMPLE_RECORD["issue_date"],
        "degree": SAMPLE_RECORD["degree"],
        "roll_no": SAMPLE_RECORD["roll_no"],
        "student_name": SAMPLE_RECORD["student_name"],
        "institution_id": SAMPLE_RECORD["institution_id"],
    }
    h1 = compute_hash(SAMPLE_RECORD, GENESIS_HASH)
    h2 = compute_hash(reordered, GENESIS_HASH)
    assert h1 == h2


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])