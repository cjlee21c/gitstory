from app.llm.client import SEMANTIC_GATE_MODEL, client
from app.llm.json_utils import extract_json

KEYWORD_PROMPT_TEMPLATE = (
    'A student described their interest as: "{interest}"\n\n'
    "Extract 2-4 short search keywords or phrases suitable for GitHub's repository search "
    "(technology names, domain terms, or topics a real popular open-source repo would be "
    "described with). Prefer single words or short two-word phrases over long phrases.\n\n"
    'Respond with ONLY a JSON array of strings, e.g. ["game engine", "rendering"]. No commentary.'
)


def extract_search_keywords(interest: str) -> list[str]:
    prompt = KEYWORD_PROMPT_TEMPLATE.format(interest=interest)
    response = client.messages.create(
        model=SEMANTIC_GATE_MODEL,
        max_tokens=100,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    keywords = extract_json(response.content[0].text)
    return [k.strip() for k in keywords if isinstance(k, str) and k.strip()][:4]
