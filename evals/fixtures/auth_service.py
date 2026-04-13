"""
auth_service.py — Authentication and session management service.
Handles user registration, login, password reset, and JWT issuance.
"""

import hmac
import hashlib
import time
import json
import base64
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional


# ------------------------------------------------------------------ #
# VULNERABILITY 1: Hardcoded Secret — JWT signing key is embedded in
# source; anyone with repo access can forge tokens.
# ------------------------------------------------------------------ #
JWT_SECRET = "s3cr3t-jwt-key-do-not-share"
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24

PASSWORD_RESET_EXPIRY_MINUTES = 30
MAX_LOGIN_ATTEMPTS = 5


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def issue_token(user_id: int, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ------------------------------------------------------------------ #
# VULNERABILITY 2: JWT Algorithm Confusion — `algorithms` accepts both
# HS256 and RS256. An attacker can obtain the public key, re-sign a
# forged token using HS256, and it will be accepted as valid.
# ------------------------------------------------------------------ #
def decode_token(token: str) -> Optional[dict]:
    try:
        # Dangerous: accepting multiple algorithms enables algorithm confusion attacks
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256", "RS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ------------------------------------------------------------------ #
# VULNERABILITY 3: Weak Password Reset Token — MD5 of email + timestamp
# is predictable. Attackers who know the email can brute-force the token
# or precompute it if the timestamp window is known.
# ------------------------------------------------------------------ #
def generate_password_reset_token(email: str) -> str:
    seed = f"{email}{int(time.time())}"
    # Dangerous: MD5 is cryptographically broken and predictable
    return hashlib.md5(seed.encode()).hexdigest()


def validate_reset_token(email: str, token: str, issued_at: int) -> bool:
    elapsed = time.time() - issued_at
    if elapsed > PASSWORD_RESET_EXPIRY_MINUTES * 60:
        return False
    expected = hashlib.md5(f"{email}{issued_at}".encode()).hexdigest()
    return hmac.compare_digest(token, expected)


# ------------------------------------------------------------------ #
# VULNERABILITY 4: Timing Attack on login — string comparison via `==`
# leaks information about how many characters matched, enabling
# character-by-character brute-forcing of valid tokens/session IDs.
# ------------------------------------------------------------------ #
def validate_api_key(provided_key: str, stored_key: str) -> bool:
    # Dangerous: non-constant-time comparison leaks timing information
    return provided_key == stored_key


def validate_api_key_safe(provided_key: str, stored_key: str) -> bool:
    return hmac.compare_digest(provided_key.encode(), stored_key.encode())


def build_login_response(user_id: int, email: str, roles: list) -> dict:
    token = issue_token(user_id, email)
    return {
        "token": token,
        "user_id": user_id,
        "email": email,
        "roles": roles,
        "issued_at": datetime.utcnow().isoformat(),
    }


def is_account_locked(failed_attempts: int) -> bool:
    return failed_attempts >= MAX_LOGIN_ATTEMPTS


def log_login_attempt(email: str, success: bool, ip: str):
    entry = {
        "email": email,
        "success": success,
        "ip": ip,
        "timestamp": datetime.utcnow().isoformat(),
    }
    print(json.dumps(entry))


# ------------------------------------------------------------------ #
# VULNERABILITY 5: Sensitive data in logs — password is written to
# stdout/log output; log aggregators (Splunk, CloudWatch) will store it.
# ------------------------------------------------------------------ #
def register_user(email: str, password: str, db):
    print(f"[DEBUG] register_user called with email={email} password={password}")
    if db.find_user(email):
        raise ValueError("Email already registered")
    hashed = hash_password(password)
    db.insert_user(email, hashed)
    return True


def change_password(user_id: int, old_password: str, new_password: str, db):
    user = db.get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found")
    if not verify_password(old_password, user["password_hash"]):
        raise ValueError("Incorrect current password")
    new_hash = hash_password(new_password)
    db.update_password(user_id, new_hash)
    return True
