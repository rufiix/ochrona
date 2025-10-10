from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
import uuid
from typing import List

from app import schemas, models, database
from .auth import get_current_user

router = APIRouter(
    prefix="/messages",
    tags=["Messaging"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/send", status_code=status.HTTP_201_CREATED, response_model=schemas.MessageMetadata)
def send_message(
    message_data: schemas.MessageSend,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Stores a new encrypted message sent from a user.

    This endpoint receives a message that has been fully encrypted and signed on
    the client side. The server's responsibility is to validate the recipients,
    and then store the encrypted payload, signature, and the per-recipient
    encrypted session keys in the database.

    Args:
        message_data (schemas.MessageSend): The payload containing the list of
            recipients, the encrypted message content, the signature, and the
            encrypted session keys for each recipient.
        db (Session): The database session dependency.
        current_user (models.User): The authenticated sender, injected by dependency.

    Raises:
        HTTPException: If any recipients are not found, or if there's a
                       server error during the transaction.

    Returns:
        schemas.MessageMetadata: Metadata for the successfully sent message.
    """
    recipient_usernames = list(set(message_data.recipients)) # Deduplicate
    if not recipient_usernames:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message must have at least one recipient.")

    recipients = db.query(models.User).filter(models.User.username.in_(recipient_usernames)).all()

    found_usernames = {user.username for user in recipients}
    if len(found_usernames) != len(recipient_usernames):
        missing_users = set(recipient_usernames) - found_usernames
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The following recipient(s) were not found: {', '.join(missing_users)}",
        )

    try:
        with db.begin_nested():
            new_message = models.Message(sender_id=current_user.id, signature=message_data.signature)
            db.add(new_message)
            db.flush()

            message_content = models.MessageContent(
                message_id=new_message.id, encrypted_payload=message_data.encrypted_payload
            )
            db.add(message_content)

            for recipient_user in recipients:
                encrypted_key = message_data.recipient_session_keys.get(recipient_user.username)
                if not encrypted_key:
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Missing encrypted session key for recipient: {recipient_user.username}"
                    )
                db.add(models.MessageRecipient(
                    message_id=new_message.id,
                    recipient_id=recipient_user.id,
                    encrypted_session_key=encrypted_key
                ))

        db.commit()
        db.refresh(new_message)

        return schemas.MessageMetadata(
            id=new_message.id,
            sender_id=new_message.sender_id,
            sender_username=current_user.username,
            created_at=new_message.created_at,
            read_status=False,
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while sending the message."
        )


@router.get("/", response_model=List[schemas.MessageMetadata])
def get_inbox_messages(
    db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)
):
    """Retrieves metadata for all messages in the authenticated user's inbox.

    This endpoint fetches a list of all messages where the current user is a
    recipient. It returns a list of message metadata objects, which include
    the sender's information, the creation timestamp, and the read status,
    but not the encrypted content itself. The results are sorted by creation
    date in descending order.

    Args:
        db (Session): The database session dependency.
        current_user (models.User): The authenticated user, injected by dependency.

    Returns:
        List[schemas.MessageMetadata]: A list of message metadata objects
                                       for the user's inbox.
    """
    recipient_entries = (
        db.query(models.MessageRecipient)
        .filter(models.MessageRecipient.recipient_id == current_user.id)
        .options(joinedload(models.MessageRecipient.message).joinedload(models.Message.sender))
        .order_by(models.MessageRecipient.message.has(models.Message.created_at.desc()))
        .all()
    )

    inbox = []
    for entry in recipient_entries:
        inbox.append(schemas.MessageMetadata(
            id=entry.message.id,
            sender_id=entry.message.sender_id,
            sender_username=entry.message.sender.username,
            created_at=entry.message.created_at,
            read_status=entry.read_status,
        ))
    return inbox


@router.get("/{message_id}", response_model=schemas.MessageFull)
def get_message_by_id(
    message_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves the full, encrypted content of a specific message.

    This endpoint fetches all the necessary components for a client to decrypt
    and verify a message: the encrypted payload, the sender's signature, and
    the session key (which itself is encrypted with the recipient's public key).

    The user must be a valid recipient of the message to access it.

    Args:
        message_id (uuid.UUID): The unique identifier of the message to retrieve.
        db (Session): The database session dependency.
        current_user (models.User): The authenticated user, injected by dependency.

    Raises:
        HTTPException: If the message is not found or the user is not a recipient.

    Returns:
        schemas.MessageFull: An object containing the full encrypted message details.
    """
    recipient_entry = (
        db.query(models.MessageRecipient)
        .filter(
            models.MessageRecipient.message_id == message_id,
            models.MessageRecipient.recipient_id == current_user.id,
        )
        .options(
            joinedload(models.MessageRecipient.message).joinedload(models.Message.content)
        )
        .first()
    )

    if not recipient_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found or you are not a recipient.")

    message = recipient_entry.message
    return schemas.MessageFull(
        id=message.id,
        sender_id=message.sender_id,
        signature=message.signature,
        encrypted_payload=message.content.encrypted_payload,
        encrypted_session_key=recipient_entry.encrypted_session_key,
        created_at=message.created_at,
    )


@router.post("/{message_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_message_as_read(
    message_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Marks a specific message as read for the authenticated user.

    This endpoint updates the `read_status` of a message recipient entry
    from False to True. It is idempotent; calling it on an already-read
    message will have no effect and will still return a success status.

    Args:
        message_id (uuid.UUID): The identifier of the message to mark as read.
        db (Session): The database session dependency.
        current_user (models.User): The authenticated user, injected by dependency.

    Raises:
        HTTPException: If the message is not found in the user's inbox.

    Returns:
        None: An empty response with a 204 No Content status code.
    """
    recipient_entry = db.query(models.MessageRecipient).filter(
        models.MessageRecipient.message_id == message_id,
        models.MessageRecipient.recipient_id == current_user.id
    ).first()

    if not recipient_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

    if not recipient_entry.read_status:
        recipient_entry.read_status = True
        db.commit()

    return


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: uuid.UUID,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Deletes a message from the authenticated user's inbox.

    This action only removes the message recipient entry for the current user.
    It does not delete the message itself or affect any other recipients of
    the same message. This operation is idempotent and will return a success
    status even if the message does not exist in the user's inbox, to prevent
    information leakage.

    Args:
        message_id (uuid.UUID): The identifier of the message to delete.
        db (Session): The database session dependency.
        current_user (models.User): The authenticated user, injected by dependency.

    Returns:
        None: An empty response with a 204 No Content status code.
    """
    recipient_entry = db.query(models.MessageRecipient).filter(
        models.MessageRecipient.message_id == message_id,
        models.MessageRecipient.recipient_id == current_user.id
    ).first()

    if recipient_entry:
        db.delete(recipient_entry)
        db.commit()

    # We return 204 regardless of whether it was found, as the end state is the same:
    # the message is not in the user's inbox. This can prevent information leakage.
    return