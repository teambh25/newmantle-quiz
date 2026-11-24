import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from answer_recommendation.candidate_generation import trend_words as tw

FIXTURE = Path(__file__).parent / "fixtures" / "trend_rss_kr.xml"
NOW = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


def rss(*items: str) -> str:
    return (
        '<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0">'
        f"<channel>{''.join(items)}</channel></rss>"
    )


def rss_item(title: str, traffic: str = "500+", news: tuple[str, ...] = ()) -> str:
    news_xml = "".join(
        f"<ht:news_item><ht:news_item_title>{n}</ht:news_item_title></ht:news_item>"
        for n in news
    )
    return (
        f"<item><title>{title}</title>"
        f"<ht:approx_traffic>{traffic}</ht:approx_traffic>{news_xml}</item>"
    )


def entry(keyword: str, traffic: int, last_seen: datetime, news=("뉴스",)) -> dict:
    iso = last_seen.isoformat()
    return {
        "keyword": keyword,
        "traffic": traffic,
        "news": list(news),
        "first_seen": iso,
        "last_seen": iso,
    }


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text, expected",
    [
        ("200+", 200),
        ("2000+", 2000),
    ],
)
def test_parse_traffic(text, expected):
    assert tw.parse_traffic(text) == expected


# only "N+" is seen in the feed; anything else means the format changed
@pytest.mark.parametrize("text", ["", None, "many", "20K+"])
def test_parse_traffic_unknown_format_raises(text):
    with pytest.raises(ValueError, match="Unknown traffic format"):
        tw.parse_traffic(text)


def test_parse_trend_rss_fixture():
    # Real feed snapshot: checks the actual structure/namespace, not its content
    trends = tw.parse_trend_rss(FIXTURE.read_text(encoding="utf-8"))

    assert len(trends) == 2
    for t in trends:
        assert set(t) == {"keyword", "traffic", "news"}
        assert isinstance(t["keyword"], str) and t["keyword"]
        assert isinstance(t["traffic"], int) and t["traffic"] > 0
        assert len(t["news"]) == 3
        assert all(isinstance(n, str) and n for n in t["news"])


def test_parse_trend_rss_missing_or_empty_news():
    xml = rss(rss_item("a"), rss_item("b", news=("", "  ")))
    trends = tw.parse_trend_rss(xml)
    assert [t["news"] for t in trends] == [[], []]


def test_parse_trend_rss_normalizes_whitespace_and_skips_empty_title():
    trends = tw.parse_trend_rss(rss(rss_item("  가나   ab  "), rss_item("  ")))
    assert [t["keyword"] for t in trends] == ["가나 ab"]


def test_parse_trend_rss_broken_xml():
    with pytest.raises(ET.ParseError):
        tw.parse_trend_rss("<rss><channel><item>")


def test_filter_trends():
    trends = [
        {"keyword": "xsmb", "traffic": 500, "news": ["n"]},
        {"keyword": "이종석", "traffic": 2000, "news": ["n"]},
        {"keyword": "고잔동", "traffic": 500, "news": []},
        {"keyword": "창원 lg 대 서울 sk", "traffic": 1000, "news": ["n"]},
    ]
    assert [t["keyword"] for t in tw.filter_trends(trends)] == [
        "이종석",
        "창원 lg 대 서울 sk",
    ]


# ---------------------------------------------------------------------------
# buffer
# ---------------------------------------------------------------------------
def test_normalize_keyword():
    assert (
        tw.normalize_keyword("  가나 AB  다 CD ")
        == tw.normalize_keyword("가나 ab 다 cd")
        == "가나 ab 다 cd"
    )


def test_prune_buffer_boundary():
    buffer = {
        "old": entry("old", 1, NOW - timedelta(hours=48, seconds=1)),
        "edge": entry("edge", 1, NOW - timedelta(hours=48)),
        "new": entry("new", 1, NOW - timedelta(hours=1)),
    }
    assert set(tw.prune_buffer(buffer, NOW, 48)) == {"edge", "new"}


def test_merge_trends_adds_new_keyword():
    merged = tw.merge_trends(
        {}, [{"keyword": "가나", "traffic": 2000, "news": ["n"]}], NOW
    )
    assert merged == {
        "가나": {
            "keyword": "가나",
            "traffic": 2000,
            "news": ["n"],
            "first_seen": NOW.isoformat(),
            "last_seen": NOW.isoformat(),
        }
    }


def test_merge_trends_updates_existing_keyword():
    earlier = NOW - timedelta(hours=2)
    buffer = {"가나 ab": entry("가나 AB", 5000, earlier, news=("old",))}

    merged = tw.merge_trends(
        buffer, [{"keyword": "가나 ab", "traffic": 1000, "news": ["new"]}], NOW
    )

    e = merged["가나 ab"]
    assert e["traffic"] == 5000  # keep the larger traffic
    assert e["news"] == ["new"]
    assert e["first_seen"] == earlier.isoformat()
    assert e["last_seen"] == NOW.isoformat()
    assert len(merged) == 1


def test_merge_trends_keeps_old_news_when_new_is_empty():
    buffer = {"a": entry("a", 100, NOW - timedelta(hours=2), news=("old",))}
    merged = tw.merge_trends(
        buffer, [{"keyword": "a", "traffic": 300, "news": []}], NOW
    )
    assert merged["a"]["news"] == ["old"]
    assert merged["a"]["traffic"] == 300


def test_merge_trends_is_idempotent_and_does_not_mutate_input():
    trends = [
        {"keyword": "a", "traffic": 100, "news": ["n1"]},
        {"keyword": "b", "traffic": 200, "news": ["n2"]},
    ]
    once = tw.merge_trends({}, trends, NOW)
    snapshot = {k: dict(v) for k, v in once.items()}

    twice = tw.merge_trends(once, trends, NOW)

    assert twice == once
    assert once == snapshot


def test_merge_trends_requires_aware_datetime():
    with pytest.raises(ValueError):
        tw.merge_trends({}, [], datetime(2026, 11, 11))


def test_select_top_trends():
    buffer = {
        "a": entry("a", 500, NOW - timedelta(hours=1), news=("na",)),
        "b": entry("b", 5000, NOW - timedelta(hours=10), news=("nb",)),
        "c": entry("c", 2000, NOW - timedelta(hours=3), news=("nc",)),
        "expired": entry("expired", 99999, NOW - timedelta(hours=49)),
    }
    assert tw.select_top_trends(buffer, NOW, hours=48, limit=2) == [
        {"keywords": ["b"], "news": ["nb"]},
        {"keywords": ["c"], "news": ["nc"]},
    ]


def test_select_top_trends_tie_breaks_by_last_seen():
    buffer = {
        "old": entry("old", 1000, NOW - timedelta(hours=5)),
        "recent": entry("recent", 1000, NOW - timedelta(hours=1)),
    }
    result = tw.select_top_trends(buffer, NOW, hours=48, limit=2)
    assert [t["keywords"] for t in result] == [["recent"], ["old"]]


def test_select_top_trends_limit_larger_than_buffer():
    buffer = {
        "a": entry("a", 100, NOW - timedelta(hours=1)),
        "b": entry("b", 200, NOW - timedelta(hours=1)),
    }
    result = tw.select_top_trends(buffer, NOW, hours=48, limit=20)
    assert [t["keywords"] for t in result] == [["b"], ["a"]]


def test_select_top_trends_empty():
    assert tw.select_top_trends({}, NOW, hours=48, limit=20) == []


# ---------------------------------------------------------------------------
# live feed (opt-in): RUN_NETWORK_TESTS=1 pytest -s
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not os.environ.get("RUN_NETWORK_TESTS"), reason="network test")
def test_fetch_trend_rss_live():
    from common.configs import TREND_RSS_URL

    trends = tw.parse_trend_rss(tw.fetch_trend_rss(TREND_RSS_URL))
    assert trends

    print(f"\n#items: {len(trends)}")
    for t in trends:
        print(f"\n{t['keyword']} ({t['traffic']})")
        for n in t["news"]:
            print(f"  - {n}")
