from trendspy import Trends


def fetch_google_trends(hours: int, num_news: int, limit: int) -> list:
    tr = Trends()
    raw_trends = tr.trending_now(geo="KR", hours=hours, num_news=num_news)

    trends = []
    for x in raw_trends:
        if len(trends) == limit:
            break
        if x.news is not None:
            trends.append(
                {"keywords": x.trend_keywords, "news": [n.title for n in x.news]}
            )
    return trends
