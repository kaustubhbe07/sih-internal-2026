"""
Unit tests for app/crypto/signing.py.

Run with: pytest app/tests/test_signing.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crypto.signing import generate_keypair, sign_hash, verify_signature
from crypto.hashing import compute_hash, GENESIS_HASH

SAMPLE_RECORD = {
    "credential_id": "cred-0001",
    "student_id": "inst-iit-demo",
    "student_name": "Aarav Sharma",
    "course_name": "B.Tech Computer Science",
    "grade": "8.7 CGPA",
    "issue_date": "2026-08-23",
}


def test_generate_keypair_returns_hex_strings():
    private_key, public_key = generate_keypair()
    assert isinstance(private_key, str)
    assert isinstance(public_key, str)
    # 32-byte Ed25519 key encoded as hex = 64 chars
    assert len(private_key) == 64
    assert len(public_key) == 64


def test_valid_signature_verifies():
    private_key, public_key = generate_keypair()
    record_hash = compute_hash(SAMPLE_RECORD, GENESIS_HASH)

    signature = sign_hash(record_hash, private_key)
    assert verify_signature(record_hash, signature, public_key) is True


def test_signature_fails_with_wrong_public_key():
    """A signature must not verify against a DIFFERENT institution's key.
    This is the core authenticity guarantee -- without this test passing,
    the whole 'digitally signed' requirement is not actually enforced."""
    private_key_a, _ = generate_keypair()
    _, public_key_b = generate_keypair()  # a different institution's key

    record_hash = compute_hash(SAMPLE_RECORD, GENESIS_HASH)
    signature = sign_hash(record_hash, private_key_a)

    assert verify_signature(record_hash, signature, public_key_b) is False


def test_signature_fails_if_record_hash_changes_after_signing():
    """If the underlying record is tampered with post-signing, the hash
    changes (see test_hashing.py), and the OLD signature must not verify
    against the NEW hash. This is what makes tampering detectable even
    if an attacker also has write access to the hash field."""
    private_key, public_key = generate_keypair()
    original_hash = compute_hash(SAMPLE_RECORD, GENESIS_HASH)
    signature = sign_hash(original_hash, private_key)

    tampered = dict(SAMPLE_RECORD)
    tampered["grade"] = "9.9 CGPA"
    tampered_hash = compute_hash(tampered, GENESIS_HASH)

    assert verify_signature(tampered_hash, signature, public_key) is False


def test_verify_signature_never_raises_on_garbage_input():
    """verify_signature must return False, not throw, on malformed input --
    callers treat 'invalid' as a normal branch, not a try/except."""
    _, public_key = generate_keypair()

    assert verify_signature("not-a-real-hash", "not-a-real-signature", public_key) is False
    assert verify_signature("", "", public_key) is False
    assert verify_signature("a" * 64, "zz" * 32, public_key) is False


def test_sign_hash_rejects_invalid_private_key():
    try:
        sign_hash("a" * 64, "not-a-valid-key")
        assert False, "expected ValueError for invalid private key"
    except ValueError:
        pass


def test_two_signatures_of_same_hash_both_verify():
    """Ed25519 signatures may or may not be deterministic depending on
    implementation details -- what must always hold is that any signature
    produced by the correct key verifies correctly, every time."""
    private_key, public_key = generate_keypair()
    record_hash = compute_hash(SAMPLE_RECORD, GENESIS_HASH)

    sig1 = sign_hash(record_hash, private_key)
    sig2 = sign_hash(record_hash, private_key)

    assert verify_signature(record_hash, sig1, public_key) is True
    assert verify_signature(record_hash, sig2, public_key) is True


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])