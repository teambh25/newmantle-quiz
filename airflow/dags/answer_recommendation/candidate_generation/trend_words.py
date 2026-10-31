import logging
import time

from trendspy import Trends

from common.utils import is_english_only

logger = logging.getLogger(__name__)


def fetch_google_trends(hours: int, max_news: int, limit: int) -> list:
    """Fetch top trends, then retrieve news separately using their tokens."""
    tr = Trends()
    raw_trends = list(tr.trending_now(geo="KR", hours=hours, num_news=0))
    candidates = [
        trend
        for trend in raw_trends
        if not is_english_only(trend.keyword) and trend.news_tokens
    ]
    candidates.sort(key=lambda trend: trend.volume or 0, reverse=True)
    logger.info(
        "Fetched %s trends; %s eligible for news retrieval; selecting up to %s",
        len(raw_trends),
        len(candidates),
        limit,
    )

    trends = []
    for trend in candidates[:limit]:
        time.sleep(0.3)
        try:
            articles = tr.trending_now_news_by_ids(trend.news_tokens, max_news=max_news)
        except Exception:
            logger.exception("Failed to fetch news for trend %r", trend.keyword)
            raise
        titles = [article.title for article in articles if article.title]
        if not titles:
            logger.info("Skipping trend %r: no news titles returned", trend.keyword)
            continue
        keywords = list(dict.fromkeys([trend.keyword, *(trend.trend_keywords or [])]))
        trends.append({"keywords": keywords, "news": titles[:max_news]})

    if not trends:
        raise ValueError("No Google Trends with news titles were collected")
    logger.info("Collected %s trends with news titles", len(trends))
    return trends
