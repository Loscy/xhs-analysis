#!/usr/bin/env python3
from datetime import datetime
import sys

from app.core.database import Base, SessionLocal, engine
from app.services.keys import create_key


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "admin"
    expires_at = datetime.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else None
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        entity, raw = create_key(db, name=name, expires_at=expires_at, can_view_devices=True, can_manage_keys=True)
        print(f"id={entity.id}")
        print(f"name={entity.name}")
        print(f"key={raw}")
        print(f"expires_at={entity.expires_at}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
