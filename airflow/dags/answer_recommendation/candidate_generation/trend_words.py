import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

from common.utils import is_english_only

RSS_NS = {"ht": "https://trends.google.com/trending/rss"}


# ---------------------------------------------------------------------------
# RSS fetch / parse
# ---------------------------------------------------------------------------
def fetch_trend_rss(url: str, geo: str = "KR", timeout: int = 15) -> str:
    resp = requests.get(url, params={"geo": geo}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def parse_traffic(text: str | None) -> int:
    """Convert approx traffic strings like '2000+' to int.

    Raises ValueError on an unknown format so a feed format change fails the
    collect task (and alerts) instead of silently ranking trends as 0.
    """
    try:
        return int((text or "").strip().removesuffix("+"))
    except ValueError:
        raise ValueError(f"Unknown traffic format: {text!r}") from None


def parse_trend_rss(xml: str) -> list[dict]:
    """Parse the Google Trends RSS feed into [{keyword, traffic, news}]."""
    trends = []
    for item in ET.fromstring(xml).findall("./channel/item"):
        keyword = " ".join((item.findtext("title") or "").split())
        if not keyword:
            continue
        news = []
        for news_item in item.findall("ht:news_item", RSS_NS):
            title = (
                news_item.findtext("ht:news_item_title", namespaces=RSS_NS) or ""
            ).strip()
            if title:
                news.append(title)
        traffic = parse_traffic(item.findtext("ht:approx_traffic", namespaces=RSS_NS))
        trends.append({"keyword": keyword, "traffic": traffic, "news": news})
    return trends


def filter_trends(trends: list[dict]) -> list[dict]:
    """Drop English-only keywords and trends without news titles."""
    return [t for t in trends if not is_english_only(t["keyword"]) and t["news"]]


# ---------------------------------------------------------------------------
# Trend buffer (stored as an Airflow Variable)
#   {normalized_keyword: {keyword, traffic, news, first_seen, last_seen}}
# ---------------------------------------------------------------------------
def normalize_keyword(keyword: str) -> str:
    return " ".join(keyword.split()).lower()


def _to_utc_iso(now: datetime) -> str:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return now.astimezone(timezone.utc).isoformat()


def prune_buffer(buffer: dict, now: datetime, hours: int) -> dict:
    """Remove entries whose last_seen is older than `hours` before `now`."""
    cutoff = now - timedelta(hours=hours)
    return {
        key: entry
        for key, entry in buffer.items()
        if datetime.fromisoformat(entry["last_seen"]) >= cutoff
    }


def merge_trends(buffer: dict, trends: list[dict], now: datetime) -> dict:
    """Merge newly fetched trends into the buffer, deduplicating by keyword."""
    now_iso = _to_utc_iso(now)
    merged = dict(buffer)
    for trend in trends:
        key = normalize_keyword(trend["keyword"])
        prev = merged.get(key)
        if prev is None:
            merged[key] = {
                "keyword": trend["keyword"],
                "traffic": trend["traffic"],
                "news": list(trend["news"]),
                "first_seen": now_iso,
                "last_seen": now_iso,
            }
            continue
        merged[key] = {
            **prev,
            "keyword": trend["keyword"],
            "traffic": max(prev["traffic"], trend["traffic"]),
            "news": list(trend["news"]) or prev["news"],
            "last_seen": now_iso,
        }
    return merged


def select_top_trends(buffer: dict, now: datetime, hours: int, limit: int) -> list:
    """Return the top `limit` recent trends in the prompt input format."""
    recent = prune_buffer(buffer, now, hours).values()
    ranked = sorted(recent, key=lambda e: (e["traffic"], e["last_seen"]), reverse=True)
    return [{"keywords": [e["keyword"]], "news": e["news"]} for e in ranked[:limit]]
