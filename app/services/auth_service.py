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
    """Schema for the data encoded within a JWT.

    Attributes:
        user_id (str | None): The user's unique identifier (subject of the token).
    """
    user_id: str | None = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a hashed password.

    Args:
        plain_password (str): The password to verify.
        hashed_password (str): The hashed password to compare against.

    Returns:
        bool: True if the password is correct, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hashes a plain-text password using the configured CryptContext.

    Args:
        password (str): The plain-text password to hash.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a new JWT access token.

    The token will contain the provided data and an expiration timestamp.

    Args:
        data (dict): The data to encode in the token (e.g., user identifier).
        expires_delta (Optional[timedelta]): The lifespan of the token. If not
            provided, a default expiration time is used.

    Returns:
        str: The encoded JWT access token.
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
    """Decodes a JWT access token and validates its signature and expiration.

    Args:
        token (str): The JWT access token to decode.

    Returns:
        Optional[TokenData]: A Pydantic model containing the token payload
                             (specifically the user_id) if the token is valid,
                             otherwise None.
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
    """Generates a new Base32 encoded secret for TOTP.

    This secret is intended to be shared with the user for them to set up
    their authenticator app.

    Returns:
        str: A new, randomly generated Base32 encoded string.
    """
    return pyotp.random_base32()


def verify_totp(otp: str, secret: str) -> bool:
    """Verifies a Time-based One-Time Password (TOTP) code.

    This function checks if the provided OTP is valid for the given secret,
    allowing for a small window to account for clock drift between the
    server and the user's device.

    Args:
        otp (str): The one-time password provided by the user.
        secret (str): The Base32 encoded secret shared with the user.

    Returns:
        bool: True if the OTP is valid, False otherwise.
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(otp, valid_window=1)


def generate_totp_uri(username: str, secret: str, issuer_name: str = "Astraea") -> str:
    """Generates a provisioning URI for authenticator apps.

    This URI can be encoded as a QR code, which users can scan with an
    authenticator app (like Google Authenticator or Authy) to automatically
    configure their TOTP generator.

    Args:
        username (str): The username to be associated with the account in the app.
        secret (str): The Base32 encoded secret for the TOTP.
        issuer_name (str): The name of the application or service.

    Returns:
        str: The provisioning URI string.
    """
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name=issuer_name
    )