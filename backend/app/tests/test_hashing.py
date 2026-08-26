"""
Unit tests for app/crypto/hashing.py.

Run with: pytest app/tests/test_hashing.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crypto.hashing import compute_hash, serialize_record, is_genesis, GENESIS_HASH

SAMPLE_RECORD = {
    "credential_id": "cred-0001",
    "student_id": "inst-iit-demo",
    "student_name": "Aarav Sharma",
    "course_name": "B.Tech Computer Science",
    "grade": "8.7 CGPA",
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
    tampered["grade"] = "9.9 CGPA"  # attacker bumps the grade
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


def test_missing_field_raises():
    incomplete = dict(SAMPLE_RECORD)
    del incomplete["grade"]
    try:
        compute_hash(incomplete, GENESIS_HASH)
        assert False, "expected KeyError for missing field"
    except KeyError:
        pass


def test_extra_fields_are_ignored_in_hash():
    """Bookkeeping fields like prev_hash/hash/signature must not affect the payload hash."""
    with_extra = dict(SAMPLE_RECORD)
    with_extra["prev_hash"] = GENESIS_HASH
    with_extra["signature"] = "not-real-but-should-be-irrelevant"

    h_clean = compute_hash(SAMPLE_RECORD, GENESIS_HASH)
    h_with_extra = compute_hash(with_extra, GENESIS_HASH)
    assert h_clean == h_with_extra


def test_is_genesis_helper():
    assert is_genesis(GENESIS_HASH) is True
    assert is_genesis("a" * 64) is False


def test_serialize_record_field_order_is_fixed():
    """Two dicts with the same data in different key order must serialize identically."""
    reordered = {
        "issue_date": SAMPLE_RECORD["issue_date"],
        "grade": SAMPLE_RECORD["grade"],
        "course_name": SAMPLE_RECORD["course_name"],
        "student_name": SAMPLE_RECORD["student_name"],
        "student_id": SAMPLE_RECORD["student_id"],
        "credential_id": SAMPLE_RECORD["credential_id"],
    }
    assert serialize_record(SAMPLE_RECORD) == serialize_record(reordered)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])