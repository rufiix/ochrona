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
    """
    Handles sending a new encrypted message.
    The server's role is to store the encrypted blobs and their relationships.
    All encryption and signing happens on the client.
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
    """
    Retrieves a list of message metadata for the authenticated user's inbox.
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
    """
    Retrieves the full, encrypted content of a specific message.
    The user must be a recipient of the message.
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
    """Marks a message as read for the current user."""
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
    """
    Deletes a message from the user's inbox by deleting their recipient record.
    This does not delete the message for other recipients.
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