import random
from datetime import timedelta
from pprint import pprint

import pendulum
from airflow.datasets.metadata import Metadata
from airflow.decorators import dag, task, task_group
from airflow.exceptions import AirflowException
from airflow.providers.postgres.hooks.postgres import PostgresHook

import answer_recommendation.candidate_generation as cg
import common.configs as configs
import common.crud as crud
import common.datasets as datasets
import common.exceptions as exc
import common.llm.gemini as gemini
import common.llm.response_schemas as rs
import common.utils as utils


@dag(
    dag_id="recommend_answer",
    start_date=pendulum.datetime(2025, 9, 26, tz="Asia/Seoul"),
    schedule="0 17 * * 0,3,5",  # every sun, wed, fri at 5pm
    catchup=False,
    tags=["schedule", "producer"],
)
def recommend_answer():
    @task
    def get_start_date(data_interval_end: pendulum.datetime) -> str:
        return data_interval_end.in_timezone("Asia/Seoul").add(days=1).to_date_string()

    @task_group(
        default_args={
            "retries": 5,
            "retry_delay": timedelta(minutes=1),
        }
    )
    def generate_candidate(start_date: str):
        @task_group
        def get_trends_words():
            @task
            def get_trends():
                trends = cg.fetch_google_trends(
                    hours=72, num_news=3, limit=20
                )  # 3 days trends
                return trends

            @task
            def extract_trend_words(trends: dict):
                prompt = utils.load_and_fill_prompt(
                    configs.PROMPTS.TREND, fill_data=utils.json_to_str(trends)
                )
                trnends_words = gemini.generation_text(
                    prompt, response_schema=list[rs.AnswerCandidate], temperature=2.0
                )
                return trnends_words

            trends = get_trends()
            trend_words = extract_trend_words(trends)
            return trend_words

        @task
        def get_common_sense_words():
            prompt = utils.load_and_fill_prompt(configs.PROMPTS.COMMON_SENSE)
            common_sense_words = gemini.generate_text_with_search(
                prompt, response_schema=list[rs.AnswerCandidate], temperature=2.0
            )
            return common_sense_words

        @task
        def get_daily_words(start_date: str):
            prompt = utils.load_and_fill_prompt(
                configs.PROMPTS.DAILY, fill_data=cg.get_korean_season(start_date)
            )
            daily_words = gemini.generate_text_with_search(
                prompt, response_schema=list[rs.AnswerCandidate], temperature=2.0
            )
            return daily_words

        @task
        def merge_and_filter_words(
            trend_words: list, common_sense_words: list, daily_words: list
        ):
            candidates = trend_words + common_sense_words + daily_words
            candidates = [x for x in candidates if utils.is_hangul_string(x["word"])]
            random.shuffle(candidates)
            print(f"#num candidate : {len(candidates)}")
            return candidates

        trend_words = get_trends_words()
        common_sense_words = get_common_sense_words()
        daily_words = get_daily_words(start_date)
        candidates = merge_and_filter_words(
            trend_words, common_sense_words, daily_words
        )
        return candidates

    @task
    def rec_n_days_answer(base_candidates: list, start_date: str, days: int):
        log = {"not_exist": [], "duplicated": [], "success": [], "skipped_date": []}
        rec_succes_dates = []
        
        for d in range(days):
            tar_date = utils.add_days(start_date, d)

            if not utils.is_future(tar_date):
                log["skipped_date"].append(tar_date)
                continue

            special_candidates = cg.get_special_day_candidate(tar_date)
            use_special_candidate = special_candidates is not None and utils.with_prob(
                configs.SPECIAL_DAY_PROB
            )
            pg_hook = PostgresHook(postgres_conn_id="quiz_db")

            while True:
                if use_special_candidate and special_candidates:
                    ans = special_candidates.pop()
                elif base_candidates:
                    ans = base_candidates.pop()
                else:
                    raise AirflowException("used all candidates")
                    # use random word_id?
                try:
                    word_id = crud.get_id_by_word_in_vocab(pg_hook, ans["word"])
                    crud.upsert_answer(
                        pg_hook, tar_date, word_id, ans["tag"], ans["description"]
                    )
                except exc.NotFoundInDB:
                    log["not_exist"].append((tar_date, ans))
                except exc.DuplicateAnswerException:
                    log["duplicated"].append((tar_date, ans))
                else:
                    log["success"].append((tar_date, ans))
                    rec_succes_dates.append(tar_date)
                    break
        log["other"] = base_candidates
        pprint(log)
        return rec_succes_dates

    @task(outlets=[datasets.answer_dataset])
    def produce_quiz_dates(dates: list):
        print(f"changed answer dates: {dates}")
        yield Metadata(datasets.answer_dataset, {"changed_answer_dates": dates})

    start_date = get_start_date()
    candidates = generate_candidate(start_date)
    rec_succes_dates = rec_n_days_answer(candidates, start_date, configs.BATCH_SIZE)
    produce_quiz_dates(rec_succes_dates)


recommend_answer()
