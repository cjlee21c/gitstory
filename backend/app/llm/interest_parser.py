from app.llm.client import SEMANTIC_GATE_MODEL, client
from app.llm.json_utils import extract_json

KEYWORD_PROMPT_TEMPLATE = (
    'A student described their interest as: "{interest}"\n\n'
    "Extract 2-4 short search keywords or phrases suitable for GitHub's repository search "
    "(technology names, domain terms, or topics a real popular open-source repo would be "
    "described with). Prefer single words or short two-word phrases over long phrases.\n\n"
    'Respond with ONLY a JSON array of strings, e.g. ["game engine", "rendering"]. No commentary.'
)


EXPAND_KEYWORD_PROMPT_TEMPLATE = (
    'A student is searching for open-source repositories in the "{domain_label}" domain '
    'and typed this keyword: "{keyword}"\n\n'
    "Clean it up (fix typos) and expand it into 2-4 short search keywords or phrases "
    "suitable for GitHub's repository search, staying within the {domain_label} domain. "
    "Prefer single words or short two-word phrases over long phrases.\n\n"
    'Respond with ONLY a JSON array of strings, e.g. ["chess engine", "chess"]. No commentary.'
)


def _run_keyword_prompt(prompt: str) -> list[str]:
    response = client.messages.create(
        model=SEMANTIC_GATE_MODEL,
        max_tokens=100,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    keywords = extract_json(response.content[0].text)
    return [k.strip() for k in keywords if isinstance(k, str) and k.strip()][:4]


def extract_search_keywords(interest: str) -> list[str]:
    return _run_keyword_prompt(KEYWORD_PROMPT_TEMPLATE.format(interest=interest))


def expand_keyword(keyword: str, domain_label: str) -> list[str]:
    return _run_keyword_prompt(
        EXPAND_KEYWORD_PROMPT_TEMPLATE.format(keyword=keyword, domain_label=domain_label)
    )
