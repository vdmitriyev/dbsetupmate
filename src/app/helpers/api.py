import os
import secrets

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext

from app.configs import logger

security = HTTPBasic()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Retrieve credentials from environment variables
USERNAME_ENV = os.getenv("BASIC_AUTH_USERNAME")
PASSWORD_ENV = os.getenv("BASIC_AUTH_PASSWORD")


# FIXME: maybe at one point hash passwords from env, not now - makes no difference
def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Authenticates a user against a single username and password stored in environment variables.
    """

    # Check if a username and password are set in environment variables
    if not USERNAME_ENV or not PASSWORD_ENV:
        logger.error("Authentication credentials not configured in environment variables.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication is not configured correctly."
        )

    # Verify the provided username against the environment variable
    is_username_correct = secrets.compare_digest(credentials.username, USERNAME_ENV)
    if not is_username_correct:
        logger.warning(f"Authentication failed: Username '{credentials.username}' not found.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Verify the provided password against the environment variable
    is_password_correct = secrets.compare_digest(credentials.password, PASSWORD_ENV)
    if not is_password_correct:
        logger.warning(f"Authentication failed: Incorrect password for user '{credentials.username}'.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    logger.debug(f"User authenticated successfully via HTTP Basic: '{credentials.username}'.")
    return credentials.username
