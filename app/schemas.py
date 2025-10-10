import uuid
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import List, Dict


# ==============================================================================
# Base Schemas
# ==============================================================================

class UserBase(BaseModel):
    """Base schema for user properties."""
    username: str = Field(..., min_length=3, max_length=50, description="The user's unique username.")


class UserCreate(UserBase):
    """Schema for creating a new user. Inherits username and adds password."""
    password: str = Field(..., min_length=12, description="User's chosen password. Must be at least 12 characters.")


class User(UserBase):
    """Schema for returning user information, excluding sensitive data like the password."""
    id: uuid.UUID = Field(..., description="The unique identifier for the user.")
    created_at: datetime = Field(..., description="The timestamp when the user account was created.")

    class Config:
        """Pydantic configuration to allow mapping from ORM models."""
        orm_mode = True


# ==============================================================================
# Authentication & Tokens
# ==============================================================================

class Token(BaseModel):
    """Schema for the JWT access token returned upon successful login."""
    access_token: str = Field(..., description="The JWT access token.")
    token_type: str = Field("bearer", description="The type of the token (always 'bearer').")


class TokenData(BaseModel):
    """Schema for the data encoded within the JWT access token."""
    username: str | None = Field(None, description="The username of the user to whom the token belongs.")


class TwoFASetup(BaseModel):
    """Schema for returning the necessary information to set up 2FA."""
    secret: str = Field(..., description="The base32 encoded secret key for the TOTP generator.")
    qr_code_uri: str = Field(..., description="A URI that can be converted to a QR code for easy setup in authenticator apps.")


# ==============================================================================
# Keys
# ==============================================================================

class KeyBase(BaseModel):
    """Base schema for cryptographic key properties."""
    public_key: str = Field(..., description="The user's public RSA key in PEM format.")
    encrypted_private_key: str = Field(..., description="The user's private RSA key, encrypted with a key derived from their password.")


class KeyCreate(KeyBase):
    """Schema for uploading a new key pair. Inherits all fields from KeyBase."""
    pass


class Key(KeyBase):
    """Schema for returning a user's key information, including database-generated fields."""
    id: uuid.UUID = Field(..., description="The unique identifier for the key pair.")
    user_id: uuid.UUID = Field(..., description="The ID of the user who owns the key.")
    key_fingerprint: str = Field(..., description="A unique fingerprint of the public key for easy identification.")
    is_active: bool = Field(..., description="A flag indicating if this is the user's primary key for new communications.")
    created_at: datetime = Field(..., description="The timestamp when the key pair was uploaded.")

    class Config:
        """Pydantic configuration to allow mapping from ORM models."""
        orm_mode = True


# ==============================================================================
# Messages
# ==============================================================================

class MessageSend(BaseModel):
    """Schema for sending a new encrypted message."""
    recipients: List[str] = Field(..., description="A list of usernames who are the recipients of the message.")
    encrypted_payload: str = Field(..., description="The message content, encrypted with a one-time AES session key.")
    signature: str = Field(..., description="A digital signature of the encrypted payload, created with the sender's private key.")
    recipient_session_keys: Dict[str, str] = Field(..., description="A dictionary mapping each recipient's username to the AES session key, which has been encrypted with that recipient's public key.")


class MessageMetadata(BaseModel):
    """Schema for returning message metadata, typically for an inbox view."""
    id: uuid.UUID = Field(..., description="The unique identifier for the message.")
    sender_id: uuid.UUID = Field(..., description="The ID of the user who sent the message.")
    sender_username: str = Field(..., description="The username of the message sender.")
    created_at: datetime = Field(..., description="The timestamp when the message was sent.")
    read_status: bool = Field(..., description="A flag indicating if the recipient has read the message.")

    class Config:
        """Pydantic configuration to allow mapping from ORM models."""
        orm_mode = True


class MessageFull(BaseModel):
    """Schema for returning the full content of a message to a specific recipient."""
    id: uuid.UUID = Field(..., description="The unique identifier for the message.")
    sender_id: uuid.UUID = Field(..., description="The ID of the user who sent the message.")
    signature: str = Field(..., description="The digital signature of the payload for verification.")
    encrypted_payload: str = Field(..., description="The encrypted message content.")
    encrypted_session_key: str = Field(..., description="The session key for this message, encrypted for the authenticated user.")
    created_at: datetime = Field(..., description="The timestamp when the message was sent.")

    class Config:
        """Pydantic configuration to allow mapping from ORM models."""
        orm_mode = True