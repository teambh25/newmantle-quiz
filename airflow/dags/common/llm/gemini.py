from google import genai
from google.genai import types

import common.configs as configs
import common.utils as utils


def generation_text(prompt: str, response_schema: list, temperature: float = 1.0) -> dict:
    client = genai.Client(api_key=configs.GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        response_schema=response_schema,
        temperature=temperature,
    )
    resp = client.models.generate_content(
        model=configs.GEMINI_MODEL,
        contents=prompt,
        config=config,
    )
    return utils.gemini_resp_to_dict(resp.text)


def generate_text_with_search(prompt: str, response_schema: list, temperature: float = 1.0) -> dict:
    client = genai.Client(api_key=configs.GEMINI_API_KEY)
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    config = types.GenerateContentConfig(
        response_schema=response_schema,
        temperature=temperature,
        tools=[grounding_tool],
    )
    resp = client.models.generate_content(
        model=configs.GEMINI_MODEL,
        contents=prompt,
        config=config,
    )
    return utils.gemini_resp_to_dict(resp.text)


if __name__ == "__main__":
    from pprint import pprint
    
    import answer_recommendation.candidate_generation as cg
    import common.llm.response_schemas as rs


    # resp = generation_text(prompt, response_schema=list[rs.AnswerCandidate])
     
    prompt = utils.load_and_fill_prompt("common/llm/prompts/daily_words.md", cg.get_korean_season("2025-09-29"))
    resp = generate_text_with_search(prompt, response_schema=list[rs.AnswerCandidate], temperature=2.0)
    
    pprint(resp)
    
