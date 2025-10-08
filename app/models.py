import uuid
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    two_fa_secret = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    keys = relationship("UserKey", back_populates="user", cascade="all, delete-orphan")
    sent_messages = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id")
    received_messages = relationship("MessageRecipient", back_populates="recipient")


class UserKey(Base):
    __tablename__ = "user_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    public_key = Column(Text, nullable=False)
    encrypted_private_key = Column(Text, nullable=False)
    key_fingerprint = Column(String(64), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="keys")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    signature = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    content = relationship("MessageContent", back_populates="message", uselist=False, cascade="all, delete-orphan")
    recipients = relationship("MessageRecipient", back_populates="message", cascade="all, delete-orphan")


class MessageContent(Base):
    __tablename__ = "message_content"

    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), primary_key=True)
    encrypted_payload = Column(Text, nullable=False)

    message = relationship("Message", back_populates="content")


class MessageRecipient(Base):
    __tablename__ = "message_recipients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    encrypted_session_key = Column(Text, nullable=False)
    read_status = Column(Boolean, default=False, nullable=False)

    message = relationship("Message", back_populates="recipients")
    recipient = relationship("User", back_populates="received_messages", foreign_keys=[recipient_id])