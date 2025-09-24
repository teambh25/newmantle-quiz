from google import genai
from google.genai import types

import common.configs as configs
import common.utils as utils


def generation_text(prompt: str, response_schema) -> dict:
    client = genai.Client(api_key=configs.GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        response_schema=response_schema,
    )
    resp = client.models.generate_content(
        model=configs.GEMINI_MODEL,
        contents=prompt,
        config=config,
    )
    return utils.gemini_resp_to_dict(resp.text)


def generate_text_with_search(prompt: str, response_schema) -> dict:
    client = genai.Client(api_key=configs.GEMINI_API_KEY)
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    config = types.GenerateContentConfig(
        response_schema=response_schema,
        tools=[grounding_tool],
    )
    resp = client.models.generate_content(
        model=configs.GEMINI_MODEL,
        contents=prompt,
        config=config,
    )
    return utils.gemini_resp_to_dict(resp.text)


if __name__ == "__main__":
    import answer_recommendation.candidate_generation as cg
    import common.llm.response_schemas as rs

    PROMPT_PATH = "common/llm/prompts/daily_words.md"

    prompt = utils.load_and_fill_prompt(PROMPT_PATH, cg.get_korean_season("2025-09-25"))
    # resp = generation_text(
    #     prompt, response_schema=list[rs.AnswerCandidate]
    # )
    resp = generate_text_with_search(prompt, response_schema=list[rs.AnswerCandidate])
    print(resp)
    # print(prompt)
