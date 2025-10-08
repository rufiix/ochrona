import uuid
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import List, Dict


# ==============================================================================
# Base Schemas
# ==============================================================================

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=12, description="Password must be at least 12 characters long.")


class User(UserBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        orm_mode = True


# ==============================================================================
# Authentication & Tokens
# ==============================================================================

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class TwoFASetup(BaseModel):
    secret: str
    qr_code_uri: str


# ==============================================================================
# Keys
# ==============================================================================

class KeyBase(BaseModel):
    public_key: str
    encrypted_private_key: str


class KeyCreate(KeyBase):
    pass


class Key(KeyBase):
    id: uuid.UUID
    user_id: uuid.UUID
    key_fingerprint: str
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True


# ==============================================================================
# Messages
# ==============================================================================

class MessageSend(BaseModel):
    recipients: List[str]  # List of recipient usernames
    encrypted_payload: str
    signature: str
    # The client sends a dictionary mapping recipient username to their encrypted session key
    recipient_session_keys: Dict[str, str]


class MessageMetadata(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    sender_username: str  # Added for convenience
    created_at: datetime
    read_status: bool

    class Config:
        orm_mode = True


class MessageFull(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    signature: str
    encrypted_payload: str
    encrypted_session_key: str # The specific key for the authenticated user
    created_at: datetime

    class Config:
        orm_mode = True