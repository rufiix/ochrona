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
    """Represents a user account in the database.

    This model stores essential user information, including their username,
    hashed password for authentication, and a secret for two-factor
    authentication. It also establishes relationships to the user's
    cryptographic keys and the messages they have sent or received.

    Attributes:
        id (UUID): The unique identifier for the user.
        username (str): The user's unique username.
        hashed_password (str): The user's password, hashed with bcrypt.
        two_fa_secret (str, optional): The secret key for TOTP 2FA.
        created_at (datetime): The timestamp when the user was created.
        updated_at (datetime): The timestamp when the user was last updated.
        keys (relationship): A one-to-many relationship to the user's keys.
        sent_messages (relationship): A one-to-many relationship to messages sent by the user.
        received_messages (relationship): A one-to-many relationship to message recipient entries.
    """
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
    """Represents a user's cryptographic key pair in the database.

    This model stores the user's public key and their encrypted private key.
    The private key is encrypted with a key derived from the user's password,
    ensuring the server never has access to the raw private key.

    Attributes:
        id (UUID): The unique identifier for the key pair.
        user_id (UUID): Foreign key linking to the user who owns this key.
        public_key (str): The user's public RSA key in PEM format.
        encrypted_private_key (str): The user's private key, encrypted.
        key_fingerprint (str): A unique fingerprint of the public key for easy identification.
        is_active (bool): Whether this key is the user's active key.
        created_at (datetime): The timestamp when the key was created.
        user (relationship): A many-to-one relationship back to the User.
    """
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
    """Represents a message entity in the database.

    This model acts as a container for a single encrypted communication. It
    links the sender to the message content and its recipients. The actual
    encrypted message data is stored in the related `MessageContent` table.

    Attributes:
        id (UUID): The unique identifier for the message.
        sender_id (UUID): Foreign key linking to the user who sent the message.
        signature (str): A digital signature of the message content, created by the sender.
        created_at (datetime): The timestamp when the message was created.
        sender (relationship): A many-to-one relationship to the sending User.
        content (relationship): A one-to-one relationship to the message's encrypted content.
        recipients (relationship): A one-to-many relationship to the message's recipients.
    """
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    signature = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    content = relationship("MessageContent", back_populates="message", uselist=False, cascade="all, delete-orphan")
    recipients = relationship("MessageRecipient", back_populates="message", cascade="all, delete-orphan")


class MessageContent(Base):
    """Stores the encrypted content of a message.

    This table holds the actual encrypted payload of a message, linking it
    directly to a `Message` entry. This separation keeps the main `messages`
    table lightweight.

    Attributes:
        message_id (UUID): The foreign key linking to the `Message` this content belongs to.
        encrypted_payload (str): The message content, encrypted with a session key.
        message (relationship): A one-to-one relationship back to the Message.
    """
    __tablename__ = "message_content"

    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), primary_key=True)
    encrypted_payload = Column(Text, nullable=False)

    message = relationship("Message", back_populates="content")


class MessageRecipient(Base):
    """Represents a recipient of a specific message.

    This table links a user (the recipient) to a message and stores the
    session key used to encrypt the message content, which has been
    individually encrypted for this specific recipient using their public key.

    Attributes:
        id (UUID): The unique identifier for this recipient entry.
        message_id (UUID): Foreign key linking to the message being sent.
        recipient_id (UUID): Foreign key linking to the user receiving the message.
        encrypted_session_key (str): The AES session key, encrypted with the recipient's public key.
        read_status (bool): A flag indicating whether the recipient has read the message.
        message (relationship): A many-to-one relationship back to the Message.
        recipient (relationship): A many-to-one relationship back to the receiving User.
    """
    __tablename__ = "message_recipients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    encrypted_session_key = Column(Text, nullable=False)
    read_status = Column(Boolean, default=False, nullable=False)

    message = relationship("Message", back_populates="recipients")
    recipient = relationship("User", back_populates="received_messages", foreign_keys=[recipient_id])