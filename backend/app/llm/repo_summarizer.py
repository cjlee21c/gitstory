import json
from app.llm.client import SEMANTIC_GATE_MODEL, client
from app.llm.json_utils import extract_json
from app.llm.usage import log_usage

SUMMARY_PROMPT_TEMPLATE = """A student is interested in: "{interest}"

Below are real GitHub repositories matching that interest, with basic stats. Select the \
{max_results} BEST candidates for a student to study REAL architectural engineering \
decisions — prioritize repos with a track record of substantive engineering discussion and \
design tradeoffs, not just popularity, and not pure tutorials/awesome-lists/toy projects.

For each selected repo, write a 1-2 sentence summary in plain language (no code, no syntax) \
explaining what makes it architecturally interesting for this interest. Keep it tight.

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
        candidates=json.dumps(_compact(candidates), separators=(",", ":")),
    )
    response = client.messages.create(
        model=SEMANTIC_GATE_MODEL,
        max_tokens=1024,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    usage = response.usage
    print(f"  [Summarize candidates] {usage.input_tokens} in / {usage.output_tokens} out tokens")
    log_usage("discover:summarize", SEMANTIC_GATE_MODEL, usage.input_tokens, usage.output_tokens)
    results = extract_json(response.content[0].text)

    # Join the LLM's chosen repos back to the original candidates to attach
    # stars/language GitHub already returned (no extra API/LLM cost).
    by_name = {c["full_name"]: c for c in candidates}
    enriched = []
    for r in results:
        if not (isinstance(r, dict) and "repo" in r and "summary" in r):
            continue
        cand = by_name.get(r["repo"], {})
        r["stars"] = cand.get("stargazers_count")
        r["language"] = cand.get("language") or None
        enriched.append(r)
    return enriched[:max_results]
