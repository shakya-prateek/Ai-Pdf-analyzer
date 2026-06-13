import hashlib
import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings


bearer_scheme = HTTPBearer(auto_error=False)
LOCAL_WORKSPACE_ID = hashlib.sha256(b"docuscope-local-workspace").hexdigest()


def workspace_id_from_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def require_workspace(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> str:
    settings = get_settings()
    if settings.single_user_mode:
        return LOCAL_WORKSPACE_ID
    if not settings.workspace_access_tokens:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Private workspace access is not configured",
        )
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Workspace access key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supplied = credentials.credentials
    matched_token = next(
        (
            token
            for token in settings.workspace_access_tokens
            if hmac.compare_digest(supplied, token)
        ),
        None,
    )
    if not matched_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid workspace access key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return workspace_id_from_token(matched_token)
