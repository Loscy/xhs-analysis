from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.entities import AndroidDevice, Product, TagQuery
from app.services.collector import adb_status_map, collect_tags
from app.services.tag_metrics import save_tag_metrics


RUNNING_STATUSES = ("pending", "running")


def busy_device_ids(db: Session) -> set[int]:
    rows = db.scalars(select(TagQuery.device_id).where(TagQuery.status == "running", TagQuery.device_id.is_not(None))).all()
    return {int(device_id) for device_id in rows if device_id}


def select_idle_device(db: Session, preferred_device_id: Optional[int] = None) -> Optional[AndroidDevice]:
    statuses = adb_status_map()
    busy_ids = busy_device_ids(db)
    query = select(AndroidDevice).where(AndroidDevice.status == "active").order_by(AndroidDevice.id)
    devices = list(db.scalars(query).all())

    if preferred_device_id is not None:
        preferred = next((device for device in devices if device.id == preferred_device_id), None)
        if preferred and preferred.id not in busy_ids and statuses.get(preferred.adb_serial, {}).get("state") == "device":
            return preferred
        return None

    for device in devices:
        if device.id in busy_ids:
            continue
        if statuses.get(device.adb_serial, {}).get("state") == "device":
            return device
    return None


def enqueue_task(db: Session, api_key_id: int, sku_id: str, source_input: str, source_url: Optional[str], product: Optional[Product], device_id: Optional[int]) -> TagQuery:
    task = TagQuery(
        sku_id=sku_id,
        status="pending",
        source_input=source_input,
        source_url=source_url,
        product_id=product.id if product else None,
        api_key_id=api_key_id,
        device_id=device_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def dispatch_pending_tasks() -> None:
    db = SessionLocal()
    try:
        pending_tasks = list(db.scalars(select(TagQuery).where(TagQuery.status == "pending").order_by(TagQuery.created_at).limit(10)).all())
        for task in pending_tasks:
            device = select_idle_device(db, task.device_id)
            if not device:
                continue
            task.status = "running"
            task.device_id = device.id
            task.started_at = datetime.utcnow()
            db.commit()
            run_task(task.id)
    finally:
        db.close()


def run_task(task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.get(TagQuery, task_id)
        if not task or task.status != "running" or not task.device_id:
            return
        device = db.get(AndroidDevice, task.device_id)
        if not device:
            task.status = "failed"
            task.error_message = "assigned device not found"
            task.finished_at = datetime.utcnow()
            db.commit()
            return
        settings = get_settings()
        try:
            result = collect_tags(sku_id=task.sku_id, serial=device.adb_serial, out_dir=settings.ui_dump_dir)
            task.status = "success"
            task.tags = result["tags"]
            task.raw_items = result["items"]
            task.elapsed_ms = result["elapsed_ms"]
            task.error_message = None
            task.finished_at = datetime.utcnow()
            if task.product_id:
                product = db.get(Product, task.product_id)
                if product:
                    product.include_detail = True
                    product.detail_status = "success"
                    product.device_collected = True
                if task.tags:
                    save_tag_metrics(db, task.sku_id, task.product_id, task.tags)
            device.last_seen_at = datetime.utcnow()
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            task.finished_at = datetime.utcnow()
            if task.product_id:
                product = db.get(Product, task.product_id)
                if product:
                    product.include_detail = True
                    product.detail_status = "failed"
        db.commit()
    finally:
        db.close()
    dispatch_pending_tasks()
