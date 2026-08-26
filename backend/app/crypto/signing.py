from __future__ import annotations

from nacl.encoding import HexEncoder
from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

def generate_keypair(institution_id: str = None) -> tuple[str, str]:
    """
    Generate an Ed25519 keypair.
    Returns (public_key_hex, private_key_hex) to match caller expectations.
    institution_id is accepted for compatibility but not used.
    """
    signing_key = SigningKey.generate()
    private_key_hex = signing_key.encode(
        encoder=HexEncoder
    ).decode("utf-8")
    public_key_hex = signing_key.verify_key.encode(
        encoder=HexEncoder
    ).decode("utf-8")
    return public_key_hex, private_key_hex


def sign_hash(record_hash: str, private_key_hex: str) -> str:
    try:
        signing_key = SigningKey(
            private_key_hex,
            encoder=HexEncoder,
        )
    except Exception as exc:
        raise ValueError(f"Invalid private key: {exc}") from exc

    signed = signing_key.sign(record_hash.encode("utf-8"))
    return signed.signature.hex()


def verify_signature(
    record_hash: str,
    signature_hex: str,
    public_key_hex: str,
) -> bool:
    try:
        verify_key = VerifyKey(
            public_key_hex,
            encoder=HexEncoder,
        )
        verify_key.verify(
            record_hash.encode("utf-8"),
            bytes.fromhex(signature_hex),
        )
        return True
    except (BadSignatureError, ValueError, TypeError):
        return False