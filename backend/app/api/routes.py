from datetime import datetime
from typing import Optional
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_api_key, require_devices_permission, require_keys_permission
from app.core.config import get_settings
from app.core.database import Base, engine, get_db
from app.core.migrations import run_lightweight_migrations
from app.models.entities import AndroidDevice, ApiKey, Product, ProductGroup, TagMetric, TagQuery
from app.schemas.dto import (
    AndroidDeviceCreate,
    AndroidDevicePublic,
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyPublic,
    TagQueryRecord,
    TagQueryResponse,
    TagQueryCreate,
    ProductCreate,
    ProductPublic,
)
from app.services.collector import CollectError, adb_status, adb_status_map, collect_tags
from app.services.keys import create_key
from app.services.scheduler import busy_device_ids, dispatch_pending_tasks, enqueue_task
from app.services.sku_resolver import SkuResolveError, resolve_sku_input
from app.services.web_goods import canonical_goods_url, refresh_product_web_data


router = APIRouter()


@router.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    run_lightweight_migrations()


@router.get("/health")
def health() -> dict:
    return {"ok": True}


@router.post("/api/keys", response_model=ApiKeyCreated)
def create_api_key(
    payload: ApiKeyCreate,
    _: Annotated[ApiKey, Depends(require_keys_permission)],
    db: Annotated[Session, Depends(get_db)],
) -> ApiKeyCreated:
    entity, raw = create_key(
        db,
        payload.name,
        payload.expires_at,
        can_view_devices=payload.can_view_devices,
        can_manage_keys=payload.can_manage_keys,
    )
    return ApiKeyCreated(
        id=entity.id,
        name=entity.name,
        key=raw,
        key_prefix=entity.key_prefix,
        expires_at=entity.expires_at,
        can_view_devices=entity.can_view_devices,
        can_manage_keys=entity.can_manage_keys,
        status=entity.status,
    )


@router.get("/me", response_model=ApiKeyPublic)
def get_me(api_key: Annotated[ApiKey, Depends(require_api_key)]) -> ApiKey:
    return api_key


@router.get("/api/keys", response_model=list[ApiKeyPublic])
def list_api_keys(
    _: Annotated[ApiKey, Depends(require_keys_permission)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ApiKey]:
    return list(db.scalars(select(ApiKey).order_by(desc(ApiKey.created_at))).all())


@router.delete("/api/keys/{key_id}")
def revoke_api_key(
    key_id: int,
    _: Annotated[ApiKey, Depends(require_keys_permission)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    entity = db.get(ApiKey, key_id)
    if not entity:
        raise HTTPException(status_code=404, detail="api key not found")
    if entity.name == "admin":
        raise HTTPException(status_code=400, detail="admin key cannot be revoked")
    entity.status = "revoked"
    db.commit()
    return {"ok": True}


@router.post("/api/devices", response_model=AndroidDevicePublic)
def upsert_device(
    payload: AndroidDeviceCreate,
    _: Annotated[ApiKey, Depends(require_devices_permission)],
    db: Annotated[Session, Depends(get_db)],
) -> AndroidDevice:
    entity = db.scalar(select(AndroidDevice).where(AndroidDevice.adb_serial == payload.adb_serial))
    if not entity:
        entity = AndroidDevice(adb_serial=payload.adb_serial, name=payload.name)
        db.add(entity)
    for key, value in payload.model_dump().items():
        setattr(entity, key, value)
    db.commit()
    db.refresh(entity)
    return entity


@router.get("/api/devices", response_model=list[AndroidDevicePublic])
def list_devices(
    _: Annotated[ApiKey, Depends(require_devices_permission)],
    db: Annotated[Session, Depends(get_db)],
) -> list[AndroidDevice]:
    return list(db.scalars(select(AndroidDevice).order_by(AndroidDevice.id)).all())


@router.get("/api/devices/status")
def device_status(_: Annotated[ApiKey, Depends(require_devices_permission)]) -> dict:
    settings = get_settings()
    return adb_status(settings.adb_serial)


@router.get("/api/devices/statuses")
def device_statuses(
    _: Annotated[ApiKey, Depends(require_devices_permission)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    statuses = adb_status_map()
    busy_ids = busy_device_ids(db)
    devices = list(db.scalars(select(AndroidDevice).order_by(AndroidDevice.id)).all())
    rows = []
    for device in devices:
        status = statuses.get(device.adb_serial)
        rows.append(
            {
                "id": device.id,
                "name": device.name,
                "adb_serial": device.adb_serial,
                "phone_ip": device.phone_ip,
                "ssh_remote_port": device.ssh_remote_port,
                "model": device.model,
                "online_status": status["state"] if status else "missing",
                "status": status["state"] if status else "missing",
                "busy": device.id in busy_ids,
                "work_status": "busy" if device.id in busy_ids else "idle",
                "detail": status["detail"] if status else "",
                "last_seen_at": device.last_seen_at,
            }
        )
    saved_serials = {device.adb_serial for device in devices}
    for serial, status in statuses.items():
        if serial not in saved_serials:
            rows.append(
                {
                    "id": None,
                    "name": serial,
                    "adb_serial": serial,
                    "phone_ip": None,
                    "ssh_remote_port": None,
                    "model": None,
                    "online_status": status["state"],
                    "status": status["state"],
                    "busy": False,
                    "work_status": "unsaved",
                    "detail": status["detail"],
                    "last_seen_at": None,
                }
            )
    return {"devices": rows}


def resolve_device(db: Session, device_id: Optional[int]) -> Optional[AndroidDevice]:
    if device_id is not None:
        device = db.get(AndroidDevice, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="device not found")
        return device
    statuses = adb_status_map()
    devices = list(db.scalars(select(AndroidDevice).where(AndroidDevice.status == "active").order_by(AndroidDevice.id)).all())
    for device in devices:
        if statuses.get(device.adb_serial, {}).get("state") == "device":
            return device
    settings = get_settings()
    return AndroidDevice(name="default", adb_serial=settings.adb_serial)


@router.get("/tags", response_model=TagQueryResponse)
def tags(
    api_key: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
    sku_id: Annotated[Optional[str], Query(alias="skuId")] = None,
    device_id: Optional[int] = Query(default=None, alias="deviceId"),
    goods_input: Optional[str] = Query(default=None, alias="input"),
) -> TagQueryResponse:
    settings = get_settings()
    device = resolve_device(db, device_id)
    serial = device.adb_serial if device else settings.adb_serial
    original_input = goods_input or sku_id or ""
    try:
        resolved = resolve_sku_input(original_input)
    except SkuResolveError as e:
        return TagQueryResponse(ok=False, sku_id="", input=original_input, error=str(e))

    try:
        result = collect_tags(sku_id=resolved.sku_id, serial=serial, out_dir=settings.ui_dump_dir)
        record = TagQuery(
            sku_id=resolved.sku_id,
            status="success",
            tags=result["tags"],
            raw_items=result["items"],
            elapsed_ms=result["elapsed_ms"],
            device_id=device.id if device and device.id else None,
            api_key_id=api_key.id,
        )
        if device and device.id:
            device.last_seen_at = datetime.utcnow()
        db.add(record)
        db.commit()
        return TagQueryResponse(
            ok=True,
            sku_id=resolved.sku_id,
            input=original_input,
            source=resolved.source,
            resolved_url=resolved.resolved_url,
            tags=result["tags"],
            items=result["items"],
            elapsed_ms=result["elapsed_ms"],
        )
    except (CollectError, RuntimeError) as e:
        record = TagQuery(
            sku_id=resolved.sku_id,
            status="failed",
            error_message=str(e),
            device_id=device.id if device and device.id else None,
            api_key_id=api_key.id,
        )
        db.add(record)
        db.commit()
        return TagQueryResponse(
            ok=False,
            sku_id=resolved.sku_id,
            input=original_input,
            source=resolved.source,
            resolved_url=resolved.resolved_url,
            error=str(e),
        )


@router.get("/resolve-sku")
def resolve_sku(
    goods_input: Annotated[str, Query(alias="input", min_length=1)],
    _: Annotated[ApiKey, Depends(require_api_key)],
) -> dict:
    resolved = resolve_sku_input(goods_input)
    return {
        "ok": True,
        "sku_id": resolved.sku_id,
        "source": resolved.source,
        "resolved_url": resolved.resolved_url,
    }


@router.get("/queries", response_model=list[TagQueryRecord])
def list_queries(
    _: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TagQuery]:
    dispatch_pending_tasks()
    return list(db.scalars(select(TagQuery).order_by(desc(TagQuery.created_at)).limit(limit)).all())


@router.post("/queries", response_model=TagQueryRecord)
def create_query(
    payload: TagQueryCreate,
    background_tasks: BackgroundTasks,
    api_key: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
) -> TagQuery:
    product = None
    source_input = payload.input or ""
    if payload.product_id:
        product = db.get(Product, payload.product_id)
        if not product:
            raise HTTPException(status_code=404, detail="product not found")
        sku_id = product.item_id
        source_input = product.source_input or product.item_id
        source_url = product.source_url
    else:
        try:
            resolved = resolve_sku_input(source_input)
        except SkuResolveError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        sku_id = resolved.sku_id
        source_url = canonical_goods_url(resolved.sku_id)
        product = upsert_product(db, sku_id=sku_id, source_input=source_input, source_url=source_url, product_type="manual")
        source_url = product.source_url

    task = enqueue_task(
        db=db,
        api_key_id=api_key.id,
        sku_id=sku_id,
        source_input=source_input,
        source_url=source_url,
        product=product,
        device_id=payload.device_id,
    )
    if product:
        product.include_detail = True
        product.detail_status = "pending"
        db.commit()
    background_tasks.add_task(dispatch_pending_tasks)
    db.refresh(task)
    return task


@router.get("/queries/{query_id}", response_model=TagQueryRecord)
def get_query(
    query_id: int,
    _: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
) -> TagQuery:
    task = db.get(TagQuery, query_id)
    if not task:
        raise HTTPException(status_code=404, detail="query not found")
    return task


def upsert_product(
    db: Session,
    sku_id: str,
    source_input: str,
    source_url: Optional[str],
    product_type: str,
    title: Optional[str] = None,
    include_detail: bool = False,
    is_main: bool = True,
    group_id: Optional[int] = None,
) -> Product:
    product = db.scalar(select(Product).where(Product.item_id == sku_id))
    if not product:
        product = Product(item_id=sku_id, web_status="pending", is_main=is_main, group_id=group_id)
        db.add(product)
    product.source_input = source_input
    product.source_url = canonical_goods_url(sku_id) or source_url
    product.type = product_type
    if include_detail:
        product.include_detail = True
        if product.detail_status == "none":
            product.detail_status = "pending"
    if title is not None:
        product.title = title
    db.commit()
    db.refresh(product)
    return product


def product_to_public(product: Product, latest_query: Optional[TagQuery] = None) -> dict:
    latest = TagQueryRecord.model_validate(latest_query).model_dump() if latest_query else None
    return {
        "id": product.id,
        "item_id": product.item_id,
        "source_input": product.source_input,
        "source_url": product.source_url,
        "type": product.type,
        "title": product.title,
        "sales_volume": product.sales_volume,
        "shop_id": product.shop_id,
        "shop_name": product.shop_name,
        "shop_url": product.shop_url,
        "shop_location": product.shop_location,
        "web_status": product.web_status,
        "web_error": product.web_error,
        "include_detail": product.include_detail,
        "detail_status": product.detail_status,
        "status": product.status,
        "is_main": product.is_main,
        "device_collected": product.device_collected,
        "original_price": product.original_price,
        "deal_price": product.deal_price,
        "group_id": product.group_id,
        "collected_at": product.collected_at,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        "latest_query": latest,
    }


@router.post("/api/products", response_model=ProductPublic)
def create_product(
    payload: ProductCreate,
    background_tasks: BackgroundTasks,
    api_key: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    try:
        resolved = resolve_sku_input(payload.input)
    except SkuResolveError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    product = upsert_product(
        db,
        sku_id=resolved.sku_id,
        source_input=payload.input,
        source_url=canonical_goods_url(resolved.sku_id),
        product_type=payload.type,
        title=payload.title,
        include_detail=payload.include_detail,
        is_main=payload.is_main,
        group_id=payload.group_id,
    )
    product = refresh_product_web_data(db, product)
    if payload.include_detail:
        task = enqueue_task(
            db=db,
            api_key_id=api_key.id,
            sku_id=resolved.sku_id,
            source_input=payload.input,
            source_url=canonical_goods_url(resolved.sku_id),
            product=product,
            device_id=payload.device_id,
        )
        product.detail_status = "pending"
        db.commit()
        background_tasks.add_task(dispatch_pending_tasks)
        db.refresh(product)
        return product_to_public(product, task)
    db.refresh(product)
    return product_to_public(product)


@router.get("/api/products/{product_id}", response_model=ProductPublic)
def get_product(
    product_id: int,
    _: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    latest_query = db.scalar(
        select(TagQuery).where(TagQuery.product_id == product.id).order_by(desc(TagQuery.created_at))
    )
    return product_to_public(product, latest_query)


@router.post("/api/products/{product_id}/refresh")
def refresh_product(
    product_id: int,
    background_tasks: BackgroundTasks,
    api_key: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    product = refresh_product_web_data(db, product)
    latest_task = None
    if product.device_collected:
        latest_task = enqueue_task(
            db=db,
            api_key_id=api_key.id,
            sku_id=product.item_id,
            source_input=product.source_input or product.item_id,
            source_url=product.source_url,
            product=product,
            device_id=None,
        )
        product.detail_status = "pending"
        db.commit()
        background_tasks.add_task(dispatch_pending_tasks)
    db.refresh(product)
    return product_to_public(product, latest_task)


@router.post("/api/products/{product_id}/detail", response_model=TagQueryRecord)
def enqueue_product_detail(
    product_id: int,
    background_tasks: BackgroundTasks,
    api_key: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
) -> TagQuery:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    product.include_detail = True
    product.detail_status = "pending"
    task = enqueue_task(
        db=db,
        api_key_id=api_key.id,
        sku_id=product.item_id,
        source_input=product.source_input or product.item_id,
        source_url=product.source_url,
        product=product,
        device_id=None,
    )
    db.commit()
    background_tasks.add_task(dispatch_pending_tasks)
    db.refresh(task)
    return task


@router.patch("/api/products/{product_id}")
def update_product(
    product_id: int,
    payload: dict,
    _: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    if "is_main" in payload:
        product.is_main = bool(payload["is_main"])
    if "group_id" in payload:
        product.group_id = payload["group_id"]
    db.commit()
    db.refresh(product)
    return product_to_public(product)


@router.get("/api/products/{product_id}/group", response_model=list[ProductPublic])
def get_product_group(
    product_id: int,
    _: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    if not product.group_id:
        return [product_to_public(product)]
    products = list(db.scalars(select(Product).where(Product.group_id == product.group_id)).all())
    all_ids = [p.id for p in products]
    latest_queries = list(db.scalars(
        select(TagQuery).where(TagQuery.product_id.in_(all_ids)).order_by(desc(TagQuery.created_at))
    ).all()) if all_ids else []
    latest_by_product: dict[int, TagQuery] = {}
    for q in latest_queries:
        if q.product_id is not None:
            latest_by_product.setdefault(q.product_id, q)
    return [product_to_public(p, latest_by_product.get(p.id)) for p in products]


@router.get("/api/products")
def list_products(
    _: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    is_main: Optional[bool] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    type: Optional[str] = Query(default=None),
    web_status: Optional[str] = Query(default=None),
    detail_status: Optional[str] = Query(default=None),
) -> dict:
    query = select(Product)
    if is_main is True:
        query = query.where(Product.is_main == True)
    if keyword:
        kw = f"%{keyword}%"
        query = query.where(
            (Product.item_id.like(kw))
            | (Product.title.like(kw))
            | (Product.shop_name.like(kw))
            | (Product.shop_location.like(kw))
            | (Product.sales_volume.like(kw))
        )
    if type:
        query = query.where(Product.type == type)
    if web_status:
        query = query.where(Product.web_status == web_status)
    if detail_status:
        if detail_status == "success":
            query = query.where(Product.include_detail == True, Product.detail_status == "success")
        elif detail_status == "none":
            query = query.where(Product.include_detail == False)
        else:
            query = query.where(Product.detail_status == detail_status)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    products = list(db.scalars(
        query.order_by(desc(Product.created_at)).offset((page - 1) * page_size).limit(page_size)
    ).all())
    all_ids = [p.id for p in products]
    latest_queries = list(db.scalars(
        select(TagQuery).where(TagQuery.product_id.in_(all_ids)).order_by(desc(TagQuery.created_at))
    ).all()) if all_ids else []
    latest_by_product: dict[int, TagQuery] = {}
    for q in latest_queries:
        if q.product_id is not None:
            latest_by_product.setdefault(q.product_id, q)
    items = [product_to_public(p, latest_by_product.get(p.id)) for p in products]
    return {"items": items, "total": total}


@router.post("/api/marketplace/collect")
def start_marketplace_collect(
    payload: dict,
    _: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    from app.services.marketplace_collector import get_progress, start_collection
    from app.core.database import SessionLocal

    current = get_progress()
    if current.status == "running":
        raise HTTPException(status_code=409, detail="collection already running")
    count = min(max(int(payload.get("count", 10)), 1), 30)
    category = payload.get("category", "T恤")
    device_id = payload.get("device_id")
    device = resolve_device(db, device_id)
    serial = device.adb_serial if device else get_settings().adb_serial
    start_collection(serial, count, category, SessionLocal)
    return {"ok": True, "count": count}


@router.get("/api/marketplace/status")
def marketplace_status(
    _: Annotated[ApiKey, Depends(require_api_key)],
) -> dict:
    from app.services.marketplace_collector import get_progress as _get_mp
    p = _get_mp()
    return {
        "status": p.status,
        "total": p.total,
        "collected": p.collected,
        "items": p.items,
        "error": p.error,
    }


@router.get("/api/tag-metrics/summary")
def tag_metrics_summary(
    _: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    subq = select(func.max(TagMetric.id).label("id")).group_by(TagMetric.sku_id, TagMetric.dim_key).subquery()
    latest_metrics = list(db.scalars(select(TagMetric).where(TagMetric.id.in_(select(subq.c.id)))).all())
    by_sku: dict[str, dict] = {}
    for m in latest_metrics:
        entry = by_sku.setdefault(m.sku_id, {"sku_id": m.sku_id, "product_id": m.product_id, "metrics": {}, "metric_updated_at": None, "_latest_dt": None})
        entry["metrics"][m.dim_key] = m.dim_value
        if m.created_at and (not entry["_latest_dt"] or m.created_at > entry["_latest_dt"]):
            entry["_latest_dt"] = m.created_at
            entry["metric_updated_at"] = m.created_at.isoformat()
    for entry in by_sku.values():
        entry.pop("_latest_dt", None)
    product_ids = list({d["product_id"] for d in by_sku.values()})
    products_map = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(product_ids))).all()} if product_ids else {}
    result = []
    for sku_id, data in by_sku.items():
        product = products_map.get(data["product_id"])
        if not product:
            continue
        result.append({
            "sku_id": sku_id,
            "product_id": product.id,
            "title": product.title,
            "shop_name": product.shop_name,
            "sales_volume": product.sales_volume,
            "original_price": product.original_price,
            "deal_price": product.deal_price,
            "product_created_at": product.created_at.isoformat(),
            "product_updated_at": product.updated_at.isoformat(),
            "metrics": data["metrics"],
            "metric_updated_at": data["metric_updated_at"],
        })
    return result


@router.get("/api/tag-metrics/history")
def tag_metrics_history(
    _: Annotated[ApiKey, Depends(require_api_key)],
    db: Annotated[Session, Depends(get_db)],
    sku_id: str = Query(...),
) -> list[dict]:
    metrics = list(db.scalars(
        select(TagMetric).where(TagMetric.sku_id == sku_id).order_by(TagMetric.created_at)
    ).all())
    return [
        {"sku_id": m.sku_id, "dim_key": m.dim_key, "dim_value": m.dim_value, "created_at": m.created_at.isoformat()}
        for m in metrics
    ]
