import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import pyotp
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Load environment variables for JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key_for_development")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

# Password Hashing Context
# Using bcrypt, which is a strong, adaptive hashing algorithm.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Pydantic model for the data encoded in the JWT."""
    user_id: str | None = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hashes a plain-text password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a new JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decodes a JWT access token. Returns the payload if valid, otherwise None.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return TokenData(user_id=user_id)
    except JWTError:
        return None


# ==============================================================================
# Two-Factor Authentication (TOTP)
# ==============================================================================

def generate_totp_secret() -> str:
    """Generates a new Base32 encoded secret for TOTP."""
    return pyotp.random_base32()


def verify_totp(otp: str, secret: str) -> bool:
    """
    Verifies a TOTP code against the secret.

    A window of 1 is allowed for clock drift between server and client.
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(otp, valid_window=1)


def generate_totp_uri(username: str, secret: str, issuer_name: str = "Astraea") -> str:
    """
    Generates a provisioning URI (for QR codes) for authenticator apps.
    """
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name=issuer_name
    )