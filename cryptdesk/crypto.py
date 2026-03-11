from __future__ import annotations

import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass, field
from hashlib import sha256

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


PASSPHRASE_KDF_ITERATIONS = 300_000
PASSPHRASE_KDF_SALT_PREFIX = b"cryptdesk-passphrase-v1"


def _b64encode(data: bytes) -> str:
    return urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return urlsafe_b64decode(text + padding)


def _derive_passphrase_material(passphrase: str, ordered_public_keys: bytes) -> bytes:
    # Derive deterministic session-bound material from the optional shared secret
    # instead of hashing the passphrase directly with a fast hash function.
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=PASSPHRASE_KDF_SALT_PREFIX + ordered_public_keys,
        iterations=PASSPHRASE_KDF_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


@dataclass(slots=True)
class Identity:
    private_key: X25519PrivateKey
    public_key_b64: str


@dataclass(slots=True)
class SessionCipher:
    send_key: bytes
    recv_key: bytes
    safety_code: str
    _encryptor: AESGCM = field(init=False, repr=False)
    _decryptor: AESGCM = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._encryptor = AESGCM(self.send_key)
        self._decryptor = AESGCM(self.recv_key)

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = os.urandom(12)
        ciphertext = self._encryptor.encrypt(nonce, plaintext, b"cryptdesk-v1")
        return nonce + ciphertext

    def decrypt(self, blob: bytes) -> bytes:
        if len(blob) < 13:
            raise ValueError("Encrypted blob is too short")
        nonce = blob[:12]
        ciphertext = blob[12:]
        return self._decryptor.decrypt(nonce, ciphertext, b"cryptdesk-v1")


def generate_identity() -> Identity:
    private_key = X25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return Identity(private_key=private_key, public_key_b64=_b64encode(public_key))


def derive_session(private_key: X25519PrivateKey, peer_public_key_b64: str, role: str, passphrase: str = "") -> SessionCipher:
    if role not in {"host", "viewer"}:
        raise ValueError(f"Unsupported role: {role}")
    local_public = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    peer_public = _b64decode(peer_public_key_b64)
    peer_key = X25519PublicKey.from_public_bytes(peer_public)
    shared_secret = private_key.exchange(peer_key)
    ordered = b"".join(sorted((local_public, peer_public)))
    passphrase_material = _derive_passphrase_material(passphrase, ordered) if passphrase else None
    key_material = HKDF(
        algorithm=hashes.SHA256(),
        length=64,
        salt=passphrase_material,
        info=b"cryptdesk-session-v1",
    ).derive(shared_secret)
    host_to_viewer = key_material[:32]
    viewer_to_host = key_material[32:]
    if role == "host":
        send_key, recv_key = host_to_viewer, viewer_to_host
    else:
        send_key, recv_key = viewer_to_host, host_to_viewer
    safety_fingerprint = sha256(ordered + key_material).hexdigest().upper()
    safety_code = "-".join(safety_fingerprint[index : index + 4] for index in range(0, 16, 4))
    return SessionCipher(send_key=send_key, recv_key=recv_key, safety_code=safety_code)
