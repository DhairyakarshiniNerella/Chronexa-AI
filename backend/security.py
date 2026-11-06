from pwdlib import PasswordHash

# Initialize password hashing
password_hash = PasswordHash.recommended()


# Convert password into secure hash
def hash_password(password: str) -> str:
    return password_hash.hash(password)


# Verify password during login
def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password
    )
import os
import jwt

from datetime import datetime, timedelta, timezone


def create_access_token(data: dict):
    secret_key = os.getenv("JWT_SECRET_KEY")

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=30)

    to_encode.update({"exp": expire})

    token = jwt.encode(
        to_encode,
        secret_key,
        algorithm="HS256"
    )

    return token