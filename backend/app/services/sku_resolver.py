import re
from dataclasses import dataclass
from typing import Optional
from urllib.error import URLError
from urllib.parse import unquote
from urllib.request import Request, urlopen


GOODS_PATTERNS = [
    re.compile(r"goods-detail/([0-9a-fA-F]{16,32})"),
    re.compile(r"goods_detail/([0-9a-fA-F]{16,32})"),
]
HEX_ID_PATTERN = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{24})(?![0-9a-fA-F])")
URL_PATTERN = re.compile(r"https?://[^\s，。'\"<>]+")
SHORT_LINK_HOSTS = ("xhslink.com", "xhsurl.com")


@dataclass
class SkuResolveResult:
    sku_id: str
    source: str
    resolved_url: Optional[str] = None


class SkuResolveError(ValueError):
    pass


def extract_sku_id(text: str) -> Optional[str]:
    decoded = unquote(text)
    for pattern in GOODS_PATTERNS:
        match = pattern.search(decoded)
        if match:
            return match.group(1).lower()
    match = HEX_ID_PATTERN.search(decoded)
    if match:
        return match.group(1).lower()
    return None


def extract_urls(text: str) -> list[str]:
    return [url.rstrip(").,，。") for url in URL_PATTERN.findall(text)]


def is_short_link(url: str) -> bool:
    return any(host in url for host in SHORT_LINK_HOSTS)


def resolve_short_link(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            )
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=8) as response:
            return response.geturl()
    except URLError as e:
        raise SkuResolveError(f"short link resolve failed: {e}") from e


def resolve_sku_input(value: str) -> SkuResolveResult:
    text = value.strip()
    if not text:
        raise SkuResolveError("empty goods input")

    direct = extract_sku_id(text)
    if direct:
        return SkuResolveResult(sku_id=direct, source="direct")

    for url in extract_urls(text):
        url_sku = extract_sku_id(url)
        if url_sku:
            return SkuResolveResult(sku_id=url_sku, source="url", resolved_url=url)
        if is_short_link(url):
            resolved_url = resolve_short_link(url)
            resolved_sku = extract_sku_id(resolved_url)
            if resolved_sku:
                return SkuResolveResult(sku_id=resolved_sku, source="short_link", resolved_url=resolved_url)

    raise SkuResolveError("no goods id found in input")
