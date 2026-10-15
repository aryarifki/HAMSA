"""
HAMSA Enterprise Security & Authentication Engine
Pure Python Standard Library implementation of PBKDF2-HMAC password hashing,
JSON Web Tokens (JWT HS256), and cryptographic token verification.
Zero external dependencies required.
"""

import os
import hmac
import json
import base64
import hashlib
import secrets
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone

DEFAULT_SECRET_KEY = os.getenv("HAMSA_SECRET_KEY", "hamsa_super_secret_jwt_key_2026_enterprise_intel")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))


def _base64url_encode(data: bytes) -> str:
    """Encodes bytes into URL-safe base64 string without trailing padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    """Decodes URL-safe base64 string with restored padding."""
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


class PasswordHasher:
    """Cryptographic password hashing using PBKDF2-HMAC-SHA256 with random salt."""

    ITERATIONS = 100_000

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hashes plaintext password into a salted PBKDF2 string."""
        salt = secrets.token_bytes(16)
        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, cls.ITERATIONS)
        return f"pbkdf2:sha256:{cls.ITERATIONS}${salt.hex()}${pwd_hash.hex()}"

    @classmethod
    def verify_password(cls, password: str, stored_hash: str) -> bool:
        """Verifies password against stored PBKDF2 hash using constant-time comparison."""
        try:
            algorithm_part, salt_hex, hash_hex = stored_hash.split("$")
            _, _, iterations_str = algorithm_part.split(":")
            iterations = int(iterations_str)
            salt = bytes.fromhex(salt_hex)
            expected_hash = bytes.fromhex(hash_hex)
            computed_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(computed_hash, expected_hash)
        except Exception:
            return False


class TokenManager:
    """High-performance pure-Python JWT generator and verifier using HMAC-SHA256."""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = (secret_key or DEFAULT_SECRET_KEY).encode("utf-8")

    def create_access_token(
        self,
        user_id: str,
        username: str,
        role: str = "investigator",
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Generates a signed JWT access token for an authenticated user."""
        now = datetime.now(timezone.utc)
        delta = expires_delta or timedelta(hours=JWT_EXPIRATION_HOURS)
        exp = now + delta

        header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
        payload = {
            "sub": user_id,
            "username": username,
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp())
        }

        header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

        encoded_header = _base64url_encode(header_bytes)
        encoded_payload = _base64url_encode(payload_bytes)

        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
        signature = hmac.new(self.secret_key, signing_input, hashlib.sha256).digest()
        encoded_signature = _base64url_encode(signature)

        return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verifies JWT signature and expiry. Returns payload dict if valid, else None."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            encoded_header, encoded_payload, encoded_signature = parts

            signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
            expected_signature = hmac.new(self.secret_key, signing_input, hashlib.sha256).digest()
            actual_signature = _base64url_decode(encoded_signature)

            if not hmac.compare_digest(expected_signature, actual_signature):
                return None

            payload_bytes = _base64url_decode(encoded_payload)
            payload = json.loads(payload_bytes.decode("utf-8"))

            # Check expiration
            exp = payload.get("exp")
            if not exp or datetime.now(timezone.utc).timestamp() > exp:
                return None

            return payload
        except Exception:
            return None


# Global Token Manager instance
GLOBAL_TOKEN_MANAGER = TokenManager()
