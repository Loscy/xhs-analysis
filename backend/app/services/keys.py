import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ApiKey


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def create_key(
    db: Session,
    name: str,
    expires_at: Optional[datetime],
    can_view_devices: bool = False,
    can_manage_keys: bool = False,
) -> Tuple[ApiKey, str]:
    is_admin = name == "admin"
    raw = "sk-" + secrets.token_urlsafe(32)
    entity = ApiKey(
        name=name,
        key_prefix=raw[:12],
        key_hash=hash_key(raw),
        expires_at=expires_at,
        can_view_devices=True if is_admin else can_view_devices,
        can_manage_keys=True if is_admin else can_manage_keys,
        status="active",
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity, raw


def verify_key(db: Session, raw_key: str) -> Optional[ApiKey]:
    if not raw_key.startswith("sk-"):
        return None
    entity = db.scalar(select(ApiKey).where(ApiKey.key_hash == hash_key(raw_key)))
    if not entity or entity.status != "active":
        return None
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if entity.expires_at and entity.expires_at < now:
        return None
    entity.last_used_at = now
    db.commit()
    db.refresh(entity)
    return entity
