import json

from app.llm.client import WORKSPACE_GEN_MODEL, client
from app.llm.json_utils import extract_json

SUMMARY_PROMPT_TEMPLATE = """A student is interested in: "{interest}"

Below are real GitHub repositories matching that interest, with basic stats. Select the \
{max_results} BEST candidates for a student to study REAL architectural engineering \
decisions — prioritize repos with a track record of substantive engineering discussion and \
design tradeoffs, not just popularity, and not pure tutorials/awesome-lists/toy projects.

For each selected repo, write a 2-3 sentence summary in plain language (no code, no syntax) \
explaining what makes it architecturally interesting for this interest.

Respond with ONLY a JSON array, no commentary:
[
  {{"repo": "<owner>/<name>", "summary": "..."}},
  ...
]

CANDIDATES:
{candidates}
"""


def _compact(candidates: list[dict]) -> list[dict]:
    return [
        {
            "repo": c["full_name"],
            "description": c.get("description") or "",
            "stars": c.get("stargazers_count", 0),
            "language": c.get("language") or "",
            "open_issues": c.get("open_issues_count", 0),
        }
        for c in candidates
    ]


def summarize_candidates(interest: str, candidates: list[dict], max_results: int = 5) -> list[dict]:
    if not candidates:
        return []

    prompt = SUMMARY_PROMPT_TEMPLATE.format(
        interest=interest,
        max_results=max_results,
        candidates=json.dumps(_compact(candidates), indent=2),
    )
    response = client.messages.create(
        model=WORKSPACE_GEN_MODEL,
        max_tokens=1024,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    results = extract_json(response.content[0].text)
    return [r for r in results if isinstance(r, dict) and "repo" in r and "summary" in r][:max_results]
