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
        model= configs.GEMINI_MODEL,
        contents=prompt,
        config=config,
    )
    return utils.gemini_resp_to_dict(resp.text)


def generate_text_with_search(prompt: str, response_schema) -> dict:
    client = genai.Client(api_key=configs.GEMINI_API_KEY)
    grounding_tool = types.Tool(
        google_search=types.GoogleSearch()
    )
    config = types.GenerateContentConfig(
        response_schema=response_schema,
        tools=[grounding_tool],
    )
    resp = client.models.generate_content(
        model= configs.GEMINI_MODEL,
        contents=prompt,
        config=config,
    )
    return utils.gemini_resp_to_dict(resp.text)