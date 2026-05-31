from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Product, ProductGroup


MALL_BASE = "https://mall.xiaohongshu.com"


class WebGoodsError(RuntimeError):
    pass


@dataclass
class WebGoodsSnapshot:
    title: Optional[str]
    sales_volume: Optional[str]
    shop_id: Optional[str]
    shop_name: Optional[str]
    shop_url: Optional[str]
    shop_location: Optional[str]
    sku_items: list[dict[str, Any]]
    raw: dict[str, Any]


def canonical_goods_url(item_id: str) -> str:
    return f"https://www.xiaohongshu.com/goods-detail/{item_id}"


def refresh_product_web_data(db: Session, product: Product) -> Product:
    product.source_url = canonical_goods_url(product.item_id)
    product.web_status = "running"
    product.web_error = None
    db.commit()
    try:
        snapshot = fetch_goods_snapshot(product.item_id)
    except Exception as e:
        product.web_status = "failed"
        product.web_error = str(e)
        db.commit()
        db.refresh(product)
        return product

    product.title = snapshot.title or product.title
    product.sales_volume = snapshot.sales_volume
    product.shop_id = snapshot.shop_id
    product.shop_name = snapshot.shop_name
    product.shop_url = snapshot.shop_url
    product.shop_location = snapshot.shop_location
    product.web_data = snapshot.raw
    product.web_status = "success"
    product.web_error = None
    product.collected_at = datetime.utcnow()

    # set price from first sku item that matches this product
    main_item = next((item for item in snapshot.sku_items if item.get("sku_id") == product.item_id), None)
    if main_item:
        product.original_price = main_item.get("original_price")
        product.deal_price = main_item.get("deal_price")

    variant_items = [item for item in snapshot.sku_items if item.get("sku_id") and item["sku_id"] != product.item_id]
    if variant_items:
        if not product.group_id:
            group = ProductGroup()
            db.add(group)
            db.flush()
            product.group_id = group.id
        for item in variant_items:
            existing = db.scalar(select(Product).where(Product.item_id == item["sku_id"]).limit(1))
            if existing:
                existing.group_id = product.group_id
                existing.title = item.get("name") or existing.title or product.title
                existing.shop_id = product.shop_id
                existing.shop_name = product.shop_name
                existing.shop_url = product.shop_url
                existing.shop_location = product.shop_location
                existing.original_price = item.get("original_price")
                existing.deal_price = item.get("deal_price")
            else:
                variant = Product(
                    item_id=item["sku_id"],
                    source_url=canonical_goods_url(item["sku_id"]),
                    type=product.type,
                    title=item.get("name") or product.title,
                    sales_volume=product.sales_volume,
                    shop_id=product.shop_id,
                    shop_name=product.shop_name,
                    shop_url=product.shop_url,
                    shop_location=product.shop_location,
                    original_price=item.get("original_price"),
                    deal_price=item.get("deal_price"),
                    web_status="success",
                    is_main=False,
                    group_id=product.group_id,
                )
                db.add(variant)

    db.commit()
    db.refresh(product)
    return product


def fetch_goods_snapshot(item_id: str) -> WebGoodsSnapshot:
    detail = _fetch_detail(item_id)
    variant = _fetch_variant(item_id)
    detail_row = _first_template_row(detail)
    variant_rows = _template_rows(variant)

    description = _dict(detail_row.get("descriptionMain")) or _dict(detail_row.get("descriptionH5"))
    selected = _dict(detail_row.get("descriptionH5"))
    price = _dict(detail_row.get("priceH5"))
    seller = _dict(detail_row.get("sellerH5"))
    distribute = _dict(detail_row.get("goodsDistributeV4"))

    title = _clean_text(description.get("name")) or _clean_text(selected.get("name"))
    sales_volume = _clean_text(price.get("itemAnalysisDataText")) or _clean_text(seller.get("salesVolume"))
    shop_url = _clean_text(seller.get("link"))

    return WebGoodsSnapshot(
        title=title,
        sales_volume=sales_volume,
        shop_id=_clean_text(seller.get("id")),
        shop_name=_clean_text(seller.get("name")),
        shop_url=shop_url,
        shop_location=_clean_text(distribute.get("location")),
        sku_items=_parse_sku_items(variant_rows),
        raw={
            "detail": _compact_detail(detail_row),
            "variant": {"count": len(variant_rows)},
        },
    )


def _fetch_detail(item_id: str) -> dict[str, Any]:
    return _fetch_json(
        "/api/store/jpd/edith/detail/h5/toc",
        {"item_id": item_id},
    )


def _fetch_variant(item_id: str) -> dict[str, Any]:
    return _fetch_json(
        "/api/store/jpd/edith/detail/h5/toc/variant",
        {"item_id": item_id},
    )


def _fetch_json(path: str, params: dict[str, str]) -> dict[str, Any]:
    url = f"{MALL_BASE}{path}?{urllib.parse.urlencode(params)}"
    headers = {
        "accept": "application/json, text/plain, */*",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
        ),
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            body = res.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise WebGoodsError(f"web api http {e.code}") from e
    except urllib.error.URLError as e:
        raise WebGoodsError(f"web api network error: {e.reason}") from e
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise WebGoodsError("web api returned invalid json") from e
    if not data.get("success"):
        raise WebGoodsError(data.get("msg") or data.get("message") or "web api rejected request")
    return data


def _template_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = ((payload.get("data") or {}).get("template_data")) or []
    return [row for row in rows if isinstance(row, dict)]


def _first_template_row(payload: dict[str, Any]) -> dict[str, Any]:
    rows = _template_rows(payload)
    if not rows:
        raise WebGoodsError("web api returned empty template data")
    return rows[0]


def _parse_sku_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for row in rows:
        content = _dict(row.get("contentE1"))
        header = _dict(row.get("headerV4"))
        fe_ext = _parse_fe_ext(_dict(content.get("instantInfo")).get("feExt"))
        sku_info = _dict(fe_ext.get("skuInfo"))
        single_variant = _dict(fe_ext.get("singleVariantInfo"))
        items.append(
            {
                "sku_id": _clean_text(content.get("id")) or _clean_text(sku_info.get("skuId")),
                "name": _clean_text(sku_info.get("name")),
                "attrs": [
                    {
                        "name": _clean_text(item.get("name")),
                        "value": _clean_text(item.get("value")),
                        "top_sale": bool(item.get("topSale")),
                    }
                    for item in content.get("variants", [])
                    if isinstance(item, dict)
                ],
                "original_price": _clean_text(header.get("priceText")) or _clean_text(single_variant.get("price")),
                "deal_price": _clean_text(header.get("dealPrice")) or _clean_text(content.get("price")),
                "image": _clean_text(single_variant.get("image")),
                "stock_status": content.get("stockStatus"),
            }
        )
    return items


def _parse_fe_ext(value: Any) -> dict[str, Any]:
    if not isinstance(value, str) or not value:
        return {}
    try:
        return json.loads(urllib.parse.unquote(value))
    except (json.JSONDecodeError, TypeError):
        return {}


def _compact_detail(row: dict[str, Any]) -> dict[str, Any]:
    keys = ["descriptionMain", "descriptionH5", "priceH5", "sellerH5", "goodsDistributeV4", "variantsParams"]
    return {key: row.get(key) for key in keys if key in row}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
