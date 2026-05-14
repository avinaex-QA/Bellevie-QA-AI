import os
from openai import OpenAI

from backend.config.env_loader import load_env_file

load_env_file()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

MODEL = "gpt-5-codex"


async def analyze_code(code_diff: str):

    prompt = f"""
    You are a Senior QA Architect.

    Analyze this code diff and provide:
    - impacted modules
    - regression risks
    - API risks
    - security concerns
    - recommended test scenarios
    - automation suggestions

    CODE DIFF:
    {code_diff}
    """

    response = client.responses.create(
        model=MODEL,
        input=prompt
    )

    return response.output_text
