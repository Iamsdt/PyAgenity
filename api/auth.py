import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel


# Models for authentication
class TokenData(BaseModel):
    sub: str | None = None
    scopes: list[str] = []


class User(BaseModel):
    username: str
    email: str | None = None
    scopes: list[str] = []


# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "pyagenity-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        scopes: list[str] = payload.get("scopes", [])
        return TokenData(sub=username, scopes=scopes)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User | None:
    """Get the current authenticated user from the JWT token."""
    if credentials is None:
        return None

    token_data = verify_token(credentials.credentials)

    # In a real implementation, you would fetch user from database
    # For now, we create a user object from token data
    return User(
        username=token_data.sub or "anonymous",
        scopes=token_data.scopes,
    )


class AuthConfig:
    """Configuration for authentication system."""

    def __init__(self, auth_config: dict[str, Any] | None = None):
        self.enabled = False
        self.auth_type = None
        self.backend = None

        if auth_config:
            self.enabled = True
            self.auth_type = auth_config.get("type", "Bearer")
            self.backend = auth_config.get("backend", "jwt")

    def require_auth(self) -> bool:
        """Check if authentication is required."""
        return self.enabled


# Global auth configuration instance
_auth_config = AuthConfig()


def init_auth_config(config: dict[str, Any] | None) -> None:
    """Initialize the global authentication configuration."""
    global _auth_config  # noqa: PLW0603
    _auth_config = AuthConfig(config)


def get_auth_config() -> AuthConfig:
    """Get the current authentication configuration."""
    return _auth_config


async def get_current_user_optional(
    user: User | None = Depends(get_current_user),
) -> User | None:
    """Get current user but don't require authentication if not configured."""
    if not get_auth_config().require_auth():
        return None
    return user


async def get_current_user_required(
    user: User | None = Depends(get_current_user),
) -> User:
    """Get current user and require authentication if configured."""
    auth_config = get_auth_config()
    if auth_config.require_auth() and user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user or User(username="anonymous")


# Create auth router
auth_router = APIRouter()


@auth_router.post("/token")
async def login_for_access_token(username: str, password: str):
    """Login endpoint to get access token."""
    # For demo purposes, accept any username/password
    # In production, implement proper user authentication
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user_required)):
    """Get current user information."""
    return current_user
