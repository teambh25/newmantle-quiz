import random

from airflow.decorators import dag, task, task_group
from airflow.exceptions import AirflowException
from airflow.providers.postgres.hooks.postgres import PostgresHook

import answer_recommendation.candidate_generation as cg
import common.configs as configs
import common.crud as crud
import common.exceptions as exc
import common.llm.gemini as gemini
import common.llm.response_schemas as rs
import common.utils as utils


@dag(dag_id="recommend_answer_test", schedule_interval=None, tags=["schedule"])
def recommend_answer():
    @task_group
    def generate_candidate():
        @task
        def get_common_sense_words():
            prompt = utils.load_prompt(configs.PROMPTS.COMMON_SENSE)
            common_sense_words = gemini.generate_text_with_search(
                prompt, response_schema=list[rs.AnswerCandidate]
            )
            return common_sense_words

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
                prompt = utils.load_prompt(configs.PROMPTS.TREND)
                prompt = utils.fill_prompt(prompt, utils.json_to_str(trends))
                trnends_words = gemini.generation_text(
                    prompt, response_schema=list[rs.AnswerCandidate]
                )
                return trnends_words

            trends = get_trends()
            trend_words = extract_trend_words(trends)
            return trend_words

        @task
        def merge_and_filter_words(common_sense_words: list, trend_words: list):
            candidates = common_sense_words + trend_words
            candidates = [x for x in candidates if utils.is_hangul_string(x["word"])]
            random.shuffle(candidates)
            print(f"#num candidate : {len(candidates)}")
            return candidates

        common_sense_words = get_common_sense_words()
        trend_words = get_trends_words()
        candidates = merge_and_filter_words(common_sense_words, trend_words)
        return candidates

    @task
    def rec_n_days_answer(start_date: str, days: int, base_candidates: list):
        for d in range(days):
            tar_date = utils.add_days(start_date, d)
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
                except exc.NotFoundInDB as e:
                    print(f"FAIL {ans['word']} : {e.msg}")
                except exc.DuplicateAnswerException as e:
                    print(f"FAIL {ans['word']} : {e.msg}")
                else:
                    print(f"SUCCESS : {tar_date} - {ans}")
                    break

    START_DATE = "2025-09-25"
    candidates = generate_candidate()
    rec_n_days_answer(START_DATE, 2, candidates)


recommend_answer()
