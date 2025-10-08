from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
import uuid

from app import schemas, models, database
from app.services import auth_service

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Dependency to get the current user from a JWT
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = auth_service.decode_access_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == uuid.UUID(token_data.user_id)).first()

    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """
    Handles user registration.
    - Validates input using Pydantic schema.
    - Checks if a user with the same username already exists.
    - Hashes the password securely before storing.
    """
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    hashed_password = auth_service.get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


from datetime import timedelta

@router.post("/login")  # Response model removed for conditional response
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)
):
    """
    Handles the first step of user login.
    - Authenticates with username/password.
    - If 2FA is enabled, issues a temporary pre-auth token.
    - If 2FA is not enabled, issues a final access token.
    """
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
        raise credentials_exception

    # If 2FA is enabled, issue a temporary token and require verification.
    if user.two_fa_secret:
        pre_auth_token = auth_service.create_access_token(
            data={"sub": str(user.id), "scope": "2fa"},
            expires_delta=timedelta(minutes=3)
        )
        return {"pre_auth_token": pre_auth_token, "token_type": "bearer", "2fa_required": True}

    # If 2FA is not enabled, issue a standard access token.
    access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login/verify-2fa", response_model=schemas.Token)
def verify_2fa_login(
    pre_auth_token: str = Depends(oauth2_scheme),
    totp_code: str = Body(..., embed=True),
    db: Session = Depends(database.get_db),
):
    """
    Handles the second step of a 2FA login.
    Verifies the pre-auth token and the TOTP code, then issues a final access token.
    """
    from jose import jwt, JWTError
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate 2FA credentials"
    )

    try:
        payload = jwt.decode(pre_auth_token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])
        if payload.get("scope") != "2fa":
            raise credentials_exception
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == uuid.UUID(user_id)).first()
    if not user or not user.two_fa_secret:
        raise credentials_exception

    if not auth_service.verify_totp(otp=totp_code, secret=user.two_fa_secret):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid 2FA code")

    # Success: issue the final access token
    access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/2fa/setup", response_model=schemas.TwoFASetup)
def setup_2fa(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)
):
    """
    Sets up Two-Factor Authentication for the current user.
    Generates and stores a new TOTP secret and returns a provisioning URI.
    """
    if current_user.two_fa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled on this account.",
        )

    secret = auth_service.generate_totp_secret()
    # In a real-world scenario, this secret MUST be encrypted at rest.
    current_user.two_fa_secret = secret
    db.add(current_user)
    db.commit()

    uri = auth_service.generate_totp_uri(current_user.username, secret)
    return {"secret": secret, "qr_code_uri": uri}