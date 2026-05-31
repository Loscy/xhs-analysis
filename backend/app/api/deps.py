from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import ApiKey
from app.services.keys import verify_key


def require_api_key(
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[Optional[str], Header()] = None,
    x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
) -> ApiKey:
    raw = x_api_key
    if not raw and authorization and authorization.lower().startswith("bearer "):
        raw = authorization.split(" ", 1)[1].strip()
    if not raw:
        raise HTTPException(status_code=401, detail="missing api key")
    key = verify_key(db, raw)
    if not key:
        raise HTTPException(status_code=401, detail="invalid or expired api key")
    return key


def require_devices_permission(api_key: Annotated[ApiKey, Depends(require_api_key)]) -> ApiKey:
    if api_key.name != "admin" and not api_key.can_view_devices:
        raise HTTPException(status_code=403, detail="device permission required")
    return api_key


def require_keys_permission(api_key: Annotated[ApiKey, Depends(require_api_key)]) -> ApiKey:
    if api_key.name != "admin" and not api_key.can_manage_keys:
        raise HTTPException(status_code=403, detail="key management permission required")
    return api_key
