import json
import re
from typing import Union

from sqlalchemy.orm import Session

from app.models.entities import TagMetric

DIMENSION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("24h_cart", re.compile(r"24小时内(\d+)\+?人加购")),
    ("7d_fav", re.compile(r"近7天新增(\d+)\+?人收藏")),
]


def save_tag_metrics(db: Session, sku_id: str, product_id: int, tags: Union[list[str], str]) -> None:
    if isinstance(tags, str):
        tags = json.loads(tags)
    for dim_key, pattern in DIMENSION_PATTERNS:
        for tag in tags:
            m = pattern.search(str(tag))
            if m:
                db.add(TagMetric(sku_id=sku_id, product_id=product_id, dim_key=dim_key, dim_value=int(m.group(1))))
    db.commit()
