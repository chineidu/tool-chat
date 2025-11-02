from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src import create_logger
from src.config import app_config, app_settings
from src.db.crud import convert_userdb_to_schema, get_user_by_username
from src.db.models import DBUser, get_db
from src.schemas import UserWithHashSchema

logger = create_logger(name="auth")
prefix: str = app_config.api_config.prefix
auth_prefix: str = app_config.api_config.auth_prefix

# =========== Configuration ===========
SECRET_KEY: str = app_settings.SECRET_KEY.get_secret_value()
ALGORITHM: str = app_settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES: int = app_settings.ACCESS_TOKEN_EXPIRE_MINUTES
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{auth_prefix}/token")

# =========== Password hashing context ===========
# Using `scrypt` instead of `bcrypt` to avoid compatibility issues on macOS
pwd_context = CryptContext(schemes=["scrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


# =========== JWT Token Management ===========
def create_access_token(
    data: dict[str, str], expires_delta: timedelta | None = None
) -> str:
    """Create a JWT access token."""
    to_encode: dict[str, Any] = data.copy()
    expire: datetime = datetime.now() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> UserWithHashSchema | None:
    """Get the current user from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict[str, Any] = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError as e:
        raise credentials_exception from e

    db_user = get_user_by_username(db=db, username=username)
    if db_user is None:
        raise credentials_exception
    return convert_userdb_to_schema(db_user)


def authenticate_user(db: Session, username: str, password: str) -> DBUser | None:
    """Authenticate user with username and password."""
    user = get_user_by_username(db, username)
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


async def get_current_active_user(
    current_user: UserWithHashSchema = Depends(get_current_user),
) -> UserWithHashSchema:  # noqa: B008
    """Get the current active user."""
    if not current_user.is_active:  # type: ignore
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
