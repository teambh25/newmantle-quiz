import json
from datetime import timedelta

import pendulum
from airflow.decorators import dag, task
from airflow.models import Variable

import answer_recommendation.candidate_generation.trend_words as tw
import common.configs as configs
import common.notifications as notifications


@dag(
    dag_id="collect_trends",
    start_date=pendulum.datetime(2026, 11, 11, tz="Asia/Seoul"),
    schedule="0 */2 * * *",  # every 2 hours
    catchup=False,
    max_active_runs=1,  # single writer of the trend buffer Variable
    default_args={
        "on_failure_callback": notifications.notify_failure,
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["schedule", "trend"],
)
def collect_trends():
    @task
    def collect_rss_trends() -> dict:
        """Fetch Google Trends RSS and merge it into the trend buffer Variable.

        The Variable is read once and written once; on any fetch/parse failure
        the task fails before writing, so the buffer is left untouched.
        """
        now = pendulum.now("UTC")

        trends = tw.parse_trend_rss(tw.fetch_trend_rss(configs.TREND_RSS_URL))
        if not trends:
            # A normal feed always has items; empty means the format/page changed
            raise ValueError("Parsed 0 trends from RSS; feed format may have changed")
        filtered = tw.filter_trends(trends)

        buffer = Variable.get(
            configs.TREND_BUFFER_VARIABLE, default_var={}, deserialize_json=True
        )
        pruned = tw.prune_buffer(buffer, now, configs.TREND_WINDOW_HOURS)
        merged = tw.merge_trends(pruned, filtered, now)

        Variable.set(
            configs.TREND_BUFFER_VARIABLE,
            json.dumps(merged, ensure_ascii=False, indent=2),
            description="Google Trends RSS buffer (managed by collect_trends DAG)",
        )

        keys = {tw.normalize_keyword(t["keyword"]) for t in filtered}
        summary = {
            "fetched": len(trends),
            "filtered": len(filtered),
            "pruned": len(buffer) - len(pruned),
            "added": len(keys - pruned.keys()),
            "updated": len(keys & pruned.keys()),
            "buffer_size": len(merged),
        }
        print(f"trend buffer summary: {summary}")
        print(f"collected keywords: {[t['keyword'] for t in filtered]}")
        return summary

    collect_rss_trends()


collect_trends()
