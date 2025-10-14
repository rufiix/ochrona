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
    """FastAPI dependency to get the current authenticated user from a JWT.

    This function is used in protected endpoints. It decodes the JWT provided
    in the Authorization header, validates it, and fetches the corresponding
    user from the database.

    Args:
        token (str): The OAuth2 bearer token.
        db (Session): The database session.

    Raises:
        HTTPException: If the token is invalid, expired, or the user is not found.

    Returns:
        models.User: The authenticated user object from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = auth_service.decode_access_token(token, expected_scope="access_token")
    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == uuid.UUID(token_data.user_id)).first()

    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """Creates a new user account.

    This endpoint handles user registration. It validates the provided username
    and password, checks for username uniqueness, hashes the password, and
    stores the new user in the database.

    Args:
        user (schemas.UserCreate): The user registration data, containing
                                   a username and password.
        db (Session): The database session dependency.

    Raises:
        HTTPException: If the username is already registered.

    Returns:
        schemas.User: The newly created user's public information.
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
    """Authenticates a user and initiates the login process.

    This endpoint handles the first step of user login. It authenticates the
    user with their username and password.

    - If 2FA is **not** enabled for the user, it returns a final JWT access token.
    - If 2FA is **enabled**, it returns a temporary pre-authentication token
      that must be used with the `/login/verify-2fa` endpoint.

    Args:
        form_data (OAuth2PasswordRequestForm): The user's login credentials
                                               (username and password).
        db (Session): The database session dependency.

    Raises:
        HTTPException: If the username or password is incorrect.

    Returns:
        dict: A dictionary containing either a final `access_token` or a
              `pre_auth_token` if 2FA is required.
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
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id), "scope": "access_token"}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login/verify-2fa", response_model=schemas.Token)
def verify_2fa_login(
    pre_auth_token: str = Depends(oauth2_scheme),
    totp_code: str = Body(..., embed=True),
    db: Session = Depends(database.get_db),
):
    """Verifies the TOTP code to complete a two-factor authentication login.

    This endpoint is the second step for users with 2FA enabled. It requires
    the `pre_auth_token` obtained from the `/login` endpoint and a valid TOTP
    code from the user's authenticator app. If both are valid, it issues a
    final, standard JWT access token.

    Args:
        pre_auth_token (str): The temporary pre-authentication token from the
                              initial login step. Passed as a Bearer token.
        totp_code (str): The Time-based One-Time Password from the user's
                         authenticator app.
        db (Session): The database session dependency.

    Raises:
        HTTPException: If the pre-auth token is invalid, the user is not found,
                       or the TOTP code is incorrect.

    Returns:
        schemas.Token: A standard JWT access token upon successful verification.
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
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id), "scope": "access_token"}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/2fa/setup", response_model=schemas.TwoFASetup)
def setup_2fa(
    current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)
):
    """Generates a new secret for setting up Two-Factor Authentication (2FA).

    This endpoint is for authenticated users who wish to enable 2FA. It
    generates a new TOTP secret, saves it to the user's record in the
    database, and returns the secret along with a provisioning URI. The URI
    can be converted into a QR code for easy scanning by authenticator apps.

    This endpoint can only be used once per account. If 2FA is already
    enabled, it will return an error.

    Args:
        current_user (models.User): The authenticated user, injected by dependency.
        db (Session): The database session dependency.

    Raises:
        HTTPException: If 2FA is already enabled for the user's account.

    Returns:
        schemas.TwoFASetup: An object containing the new TOTP secret and the
                            provisioning URI for QR code generation.
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