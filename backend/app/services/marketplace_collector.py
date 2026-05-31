from __future__ import annotations

import re
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Product, TagQuery
from app.services.collector import extract_tags_from_xml, screen_size, unique_preserve
from app.services.tag_metrics import save_tag_metrics
from app.services.web_goods import canonical_goods_url, refresh_product_web_data


CATEGORIES = {
    "T恤": "穿搭",
}


@dataclass
class CollectProgress:
    status: str = "idle"
    total: int = 0
    collected: int = 0
    items: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""


_progress = CollectProgress()


def get_progress() -> CollectProgress:
    return _progress


def _adb(serial: str, args: list[str], timeout: int = 30) -> str:
    cmd = ["adb", "-s", serial] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip()


def _dump_ui(serial: str) -> str:
    _adb(serial, ["shell", "uiautomator", "dump", "/sdcard/ui.xml"], timeout=15)
    return _adb(serial, ["shell", "cat", "/sdcard/ui.xml"], timeout=10)


def _tap(serial: str, x: int, y: int) -> None:
    _adb(serial, ["shell", "input", "tap", str(x), str(y)])


def _back(serial: str) -> None:
    _adb(serial, ["shell", "input", "keyevent", "KEYCODE_BACK"])


def _scroll(serial: str) -> None:
    _adb(serial, ["shell", "input", "swipe", "540", "1800", "540", "400", "400"])


def _get_detail_item_id(serial: str) -> Optional[str]:
    output = _adb(serial, ["shell", "dumpsys", "activity", "activities"], timeout=15)
    for line in output.split("\n"):
        if "dat=xhsdiscover://goods_detail/" in line and "GoodsDetail" in line:
            match = re.search(r"xhsdiscover://goods_detail/([a-f0-9]+)", line)
            if match:
                return match.group(1)
    return None


def _find_product_cards(xml_str: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return []

    cards = []
    for node in root.iter():
        if node.get("clickable") != "true":
            continue
        bounds_str = node.get("bounds", "")
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
        if not m:
            continue
        x1, y1, x2, y2 = (int(m.group(i)) for i in range(1, 5))
        width, height = x2 - x1, y2 - y1
        if width < 200 or height < 300:
            continue

        has_image = False
        text_count = 0
        title_text = ""
        price_text = ""

        for child in node.iter():
            if child is node:
                continue
            if child.get("class") == "android.widget.ImageView":
                has_image = True
            text = (child.get("text") or "").strip()
            desc = child.get("content-desc") or ""
            if text:
                text_count += 1
                if not title_text and len(text) > 2 and not text.startswith("¥"):
                    title_text = text
            if desc and ("¥" in desc or "已售" in desc):
                price_text = desc

        if has_image and text_count >= 1:
            cards.append({
                "cx": (x1 + x2) // 2,
                "cy": (y1 + y2) // 2,
                "title": title_text,
                "price": price_text,
            })

    cards.sort(key=lambda c: (c["cy"], c["cx"]))
    return cards


def _find_node_center(xml_str: str, text: str) -> Optional[tuple[int, int]]:
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return None
    for node in root.iter():
        node_text = (node.get("text") or "").strip()
        node_desc = (node.get("content-desc") or "").strip()
        if node_text == text or node_desc == text:
            bounds_str = node.get("bounds", "")
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
            if m:
                return ((int(m.group(1)) + int(m.group(3))) // 2,
                        (int(m.group(2)) + int(m.group(4))) // 2)
    return None


def _find_clickable_ancestor_center(xml_str: str, text: str) -> Optional[tuple[int, int]]:
    """Find the clickable ancestor of a node matching text/desc, return its center."""
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return None
    target = None
    for node in root.iter():
        node_text = (node.get("text") or "").strip()
        node_desc = (node.get("content-desc") or "").strip()
        if node_text == text or node_desc == text:
            target = node
            break
    if target is None:
        return None
    # Walk up to find clickable parent
    node = target
    for _ in range(10):
        bounds_str = node.get("bounds", "")
        if node.get("clickable") == "true":
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
            if m:
                return ((int(m.group(1)) + int(m.group(3))) // 2,
                        (int(m.group(2)) + int(m.group(4))) // 2)
        # Find parent by walking the tree
        parent = _find_parent(root, node)
        if parent is None:
            break
        node = parent
    # Fallback: return the target's own center
    bounds_str = target.get("bounds", "")
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
    if m:
        return ((int(m.group(1)) + int(m.group(3))) // 2,
                (int(m.group(2)) + int(m.group(4))) // 2)
    return None


def _find_parent(root: ET.Element, target: ET.Element) -> Optional[ET.Element]:
    for parent in root.iter():
        for child in parent:
            if child is target:
                return parent
    return None


def _extract_tags_from_detail(serial: str, xml_str: str) -> list[str]:
    _, height = screen_size(serial)
    items = extract_tags_from_xml(xml_str, height)
    items = unique_preserve(items)
    return [item["text"] for item in items]


def _navigate_to_category(serial: str, category: str) -> None:
    tab_name = CATEGORIES.get(category)
    if not tab_name:
        raise RuntimeError(f"unsupported category: {category}")

    # Clear XHS task stack and launch fresh main page
    _adb(serial, ["shell", "am", "force-stop", "com.xingin.xhs"])
    time.sleep(1)
    _adb(serial, ["shell", "am", "start", "-n", "com.xingin.xhs/.index.v2.IndexActivityV2"])
    time.sleep(4)

    # Find and click marketplace tab
    xml_str = _dump_ui(serial)
    pos = _find_clickable_ancestor_center(xml_str, "市集")
    if not pos:
        raise RuntimeError("could not find 市集 tab on XHS main page")
    _tap(serial, pos[0], pos[1])
    time.sleep(3)

    # Find and click category tab (e.g. 穿搭)
    xml_str = _dump_ui(serial)
    pos = _find_clickable_ancestor_center(xml_str, tab_name)
    if not pos:
        raise RuntimeError(f"could not find '{tab_name}' tab on marketplace page")
    _tap(serial, pos[0], pos[1])
    time.sleep(2)

    # Find and click sub-category (e.g. T恤) in the grid
    xml_str = _dump_ui(serial)
    pos = _find_node_center(xml_str, category)
    if not pos:
        raise RuntimeError(f"could not find sub-category '{category}' on marketplace page")
    _tap(serial, pos[0], pos[1])
    time.sleep(3)


def _collect_serial(
    serial: str,
    count: int,
    category: str,
    session_factory: Callable[[], Session],
) -> None:
    global _progress
    _progress = CollectProgress(status="running", total=count)

    try:
        _navigate_to_category(serial, category)
    except Exception as e:
        _progress.status = "error"
        _progress.error = f"navigation failed: {e}"
        return

    seen_item_ids: set[str] = set()
    no_new_rounds = 0

    try:
        for _ in range(25):
            if _progress.collected >= count:
                break
            if no_new_rounds >= 3:
                break

            xml_str = _dump_ui(serial)
            cards = _find_product_cards(xml_str)

            new_found = False
            for card in cards:
                if _progress.collected >= count:
                    break

                _tap(serial, card["cx"], card["cy"])
                time.sleep(2.5)

                item_id = _get_detail_item_id(serial)
                if not item_id or item_id in seen_item_ids:
                    _back(serial)
                    time.sleep(1.5)
                    continue

                seen_item_ids.add(item_id)
                new_found = True

                # Collect tags from the detail page while we're here
                tags: list[str] = []
                detail_xml = _dump_ui(serial)
                if detail_xml:
                    tags = _extract_tags_from_detail(serial, detail_xml)

                db = session_factory()
                try:
                    product = db.scalar(select(Product).where(Product.item_id == item_id))
                    if not product:
                        product = Product(
                            item_id=item_id,
                            source_url=canonical_goods_url(item_id),
                            type="marketplace",
                            title=card["title"] or None,
                            web_status="pending",
                            is_main=True,
                        )
                        db.add(product)
                        db.commit()
                        db.refresh(product)
                        try:
                            refresh_product_web_data(db, product)
                        except Exception:
                            pass
                    # Save collected tags
                    if tags:
                        product.include_detail = True
                        product.detail_status = "success"
                        product.device_collected = True
                        record = TagQuery(
                            sku_id=item_id,
                            status="success",
                            tags=tags,
                            raw_items=[{"text": t} for t in tags],
                            product_id=product.id,
                        )
                        db.add(record)
                        save_tag_metrics(db, item_id, product.id, tags)
                        db.commit()
                except Exception:
                    pass
                finally:
                    db.close()

                _progress.collected += 1
                _progress.items.append({
                    "item_id": item_id,
                    "title": card["title"],
                    "price": card["price"],
                    "tags": tags,
                })

                _back(serial)
                time.sleep(1.5)

            if not new_found:
                no_new_rounds += 1
            else:
                no_new_rounds = 0

            if _progress.collected < count:
                _scroll(serial)
                time.sleep(2)

        _progress.status = "done"
    except Exception as e:
        _progress.status = "error"
        _progress.error = str(e)


def start_collection(
    serial: str,
    count: int,
    category: str,
    session_factory: Callable[[], Session],
) -> None:
    thread = threading.Thread(
        target=_collect_serial,
        args=(serial, count, category, session_factory),
        daemon=True,
    )
    thread.start()
