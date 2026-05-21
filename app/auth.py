import os
from fastapi import Header, HTTPException, status


def verify_token(authorization: str = Header(None)):
    """FastAPI dependency to verify a Bearer token if `AUTH_TOKEN` is set.

    If `AUTH_TOKEN` is empty, verification is skipped (open access).
    """
    auth_token = os.getenv("AUTH_TOKEN", "")
    if auth_token:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
        token = authorization.split(" ", 1)[1]
        if token != auth_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return True
