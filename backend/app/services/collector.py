import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple


TAG_PATTERNS = [
    re.compile(r".*退货包运费.*"),
    re.compile(r".*7天无理由$"),
    re.compile(r".*正在看.*"),
    re.compile(r".*加购.*"),
    re.compile(r".*收藏.*"),
    re.compile(r".*近\d+天.*"),
    re.compile(r".*\d+\+人.*"),
    re.compile(r".*TOP\d+.*"),
    re.compile(r".*销量TOP\d+.*"),
    re.compile(r".*店铺新品.*"),
    re.compile(r".*近期店铺.*"),
]

EXCLUDE_PATTERNS = [
    re.compile(r".*服务说明.*"),
    re.compile(r".*商品评价.*"),
    re.compile(r".*加入购物车.*"),
    re.compile(r".*购物车.*"),
    re.compile(r".*领券购买.*"),
    re.compile(r".*7天无理由退货.*"),
]


class CollectError(RuntimeError):
    pass


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and p.returncode != 0:
        raise CollectError(
            f"command failed ({p.returncode}): {' '.join(cmd)}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"
        )
    return p


def adb(serial: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", serial, *args], check=check)


def screen_size(serial: str) -> Tuple[int, int]:
    out = adb(serial, "shell", "wm", "size").stdout
    m = re.search(r"Physical size:\s*(\d+)x(\d+)", out)
    if not m:
        return 1080, 2400
    return int(m.group(1)), int(m.group(2))


def open_goods(serial: str, sku_id: str) -> None:
    adb(
        serial,
        "shell",
        "am",
        "start",
        "-a",
        "android.intent.action.VIEW",
        "-d",
        f"xhsdiscover://goods_detail/{sku_id}",
        "com.xingin.xhs",
    )


def dump_xml(serial: str, out_path: Path) -> Optional[str]:
    adb(serial, "shell", "uiautomator", "dump", "/sdcard/window.xml", check=False)
    p = adb(serial, "shell", "cat", "/sdcard/window.xml", check=False)
    if not p.stdout.strip().startswith("<?xml"):
        return None
    out_path.write_text(p.stdout, encoding="utf-8")
    return p.stdout


def clean_text(value: Optional[str]) -> str:
    return re.sub(r"\s+", "", value or "").strip()


def looks_like_tag(text: str) -> bool:
    if not text or len(text) > 30:
        return False
    if any(p.fullmatch(text) for p in EXCLUDE_PATTERNS):
        return False
    return any(p.fullmatch(text) for p in TAG_PATTERNS)


def parse_bounds(bounds: Optional[str]) -> Optional[Tuple[int, int, int, int]]:
    m = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds or "")
    if not m:
        return None
    return tuple(map(int, m.groups()))


def extract_tags_from_xml(xml_text: str, screen_height: int) -> list[dict]:
    root = ET.fromstring(xml_text)
    candidates = []
    for node in root.iter("node"):
        bounds = parse_bounds(node.attrib.get("bounds", ""))
        for attr in ("text", "content-desc"):
            text = clean_text(node.attrib.get(attr, ""))
            if looks_like_tag(text):
                candidates.append({"text": text, "bounds": bounds, "source": attr})

    filtered = []
    for item in candidates:
        bounds = item["bounds"]
        if not bounds:
            filtered.append(item)
            continue
        _, y1, _, y2 = bounds
        if 0.45 <= y1 / screen_height <= 0.94 or 0.45 <= y2 / screen_height <= 0.94:
            filtered.append(item)
    return filtered or candidates


def page_has_load_error(xml_text: str) -> bool:
    return "商品加载失败" in xml_text or "请稍后再试" in xml_text


def unique_preserve(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for item in items:
        text = item["text"]
        if text not in seen:
            seen.add(text)
            out.append(item)
    return out


def swipe_tags(serial: str, width: int, height: int, y: Optional[int] = None) -> None:
    y = y if y is not None else int(height * 0.70)
    adb(
        serial,
        "shell",
        "input",
        "swipe",
        str(int(width * 0.86)),
        str(y),
        str(int(width * 0.18)),
        str(y),
        "450",
        check=False,
    )


def collect_tags(
    sku_id: str,
    serial: str,
    out_dir: str,
    wait: float = 2.2,
    swipes: int = 1,
    settle: float = 0.35,
) -> dict:
    started = time.time()
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    width, height = screen_size(serial)
    open_goods(serial, sku_id)
    time.sleep(wait)

    all_items: list[dict] = []
    seen_texts: set[str] = set()
    no_new_rounds = 0
    last_tag_y = None
    for index in range(swipes + 1):
        xml_text = dump_xml(serial, path / f"{sku_id}-{index}.xml")
        if xml_text:
            if page_has_load_error(xml_text):
                raise CollectError("goods page loaded but shows 商品加载失败，请稍后再试")
            round_items = extract_tags_from_xml(xml_text, height)
            before = len(seen_texts)
            for item in round_items:
                all_items.append(item)
                seen_texts.add(item["text"])
            no_new_rounds = no_new_rounds + 1 if len(seen_texts) == before else 0
            centers = [(b[1] + b[3]) // 2 for item in round_items if (b := item.get("bounds"))]
            if centers:
                centers.sort()
                last_tag_y = centers[len(centers) // 2]
            if index > 0 and no_new_rounds >= 1:
                break
        if index < swipes:
            swipe_tags(serial, width, height, last_tag_y)
            time.sleep(settle)

    items = unique_preserve(all_items)
    return {
        "sku_id": sku_id,
        "serial": serial,
        "tags": [item["text"] for item in items],
        "items": items,
        "elapsed_ms": int((time.time() - started) * 1000),
    }


def adb_status(serial: str) -> dict:
    p = run(["adb", "devices", "-l"], check=False)
    state = "missing"
    detail = ""
    for line in p.stdout.splitlines():
        if line.startswith(serial):
            parts = line.split(None, 2)
            state = parts[1] if len(parts) > 1 else "unknown"
            detail = parts[2] if len(parts) > 2 else ""
    return {"serial": serial, "state": state, "detail": detail, "raw": p.stdout}


def adb_status_map() -> dict:
    p = run(["adb", "devices", "-l"], check=False)
    statuses = {}
    for line in p.stdout.splitlines():
        if not line.strip() or line.startswith("List of devices"):
            continue
        parts = line.split(None, 2)
        if len(parts) >= 2:
            statuses[parts[0]] = {
                "serial": parts[0],
                "state": parts[1],
                "detail": parts[2] if len(parts) > 2 else "",
                "raw": p.stdout,
            }
    return statuses
