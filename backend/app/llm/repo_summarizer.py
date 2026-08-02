import json

from app.llm.client import SEMANTIC_GATE_MODEL, client
from app.llm.json_utils import extract_json
from app.llm.usage import log_usage

SELECTION_CRITERIA = """prioritize repos with a track record of substantive engineering \
discussion and design tradeoffs, not just popularity, and not pure tutorials/awesome-lists/\
toy projects"""

# Ranking the whole pool but summarizing only the first page keeps the blocking
# call short: output tokens are generated serially, so summarizing all of the
# pool up front roughly triples how long the student waits. The rest is filled
# in by fill_summaries() after the response has already been sent.
RANK_PROMPT_TEMPLATE = """A student is interested in: "{interest}"

Below are real GitHub repositories matching that interest, with basic stats. Rank the \
{pool_size} BEST candidates for a student to study REAL architectural engineering \
decisions — {criteria}.

Then, for the FIRST {summary_count} repos in your ranking only, write ONE sentence of at most \
25 words, in plain language (no code, no syntax), explaining what makes it architecturally \
interesting for this interest.

Respond with ONLY this JSON object, no commentary:
{{
  "ranked": ["<owner>/<name>", ...],
  "summaries": [{{"repo": "<owner>/<name>", "summary": "..."}}, ...]
}}

CANDIDATES:
{candidates}
"""

SUMMARY_ONLY_PROMPT_TEMPLATE = """A student is interested in: "{interest}"

For each GitHub repository below, write ONE sentence of at most 25 words, in plain language \
(no code, no syntax), explaining what makes it architecturally interesting for this \
interest — {criteria}.

Respond with ONLY a JSON array, no commentary:
[
  {{"repo": "<owner>/<name>", "summary": "..."}},
  ...
]

REPOSITORIES:
{candidates}
"""


# Legit GitHub descriptions top out near 350 chars; spam/SEO repos stuff tens of
# thousands of chars in here, which can blow the summarizer prompt past the model's
# context limit (a 400 "prompt is too long"). Cap it well above the honest max.
# 250 rather than 500: descriptions are the bulk of the prompt now that the
# candidate list is larger, and the back half of a long one never changes the pick.
MAX_DESC_CHARS = 250


def _compact(candidates: list[dict]) -> list[dict]:
    return [
        {
            "repo": c["full_name"],
            "description": (c.get("description") or "")[:MAX_DESC_CHARS],
            "stars": c.get("stargazers_count", 0),
            "language": c.get("language") or "",
            "open_issues": c.get("open_issues_count", 0),
        }
        for c in candidates
    ]


def _enrich(entries: list[dict], by_name: dict[str, dict]) -> list[dict]:
    """Attach stars/language GitHub already returned (no extra API/LLM cost).
    Drops anything the model invented that wasn't in the candidate list."""
    out = []
    for e in entries:
        if not (isinstance(e, dict) and "repo" in e and "summary" in e):
            continue
        cand = by_name.get(e["repo"])
        if cand is None:
            continue
        out.append(
            {
                "repo": e["repo"],
                "summary": e["summary"],
                "stars": cand.get("stargazers_count"),
                "language": cand.get("language") or None,
            }
        )
    return out


def rank_and_summarize(
    interest: str,
    candidates: list[dict],
    pool_size: int = 15,
    summary_count: int = 5,
) -> list[dict]:
    """Ordered pool of up to `pool_size` repos, best first.

    Only the first `summary_count` entries carry a summary; the rest come back
    with summary="" for fill_summaries() to complete in the background. Callers
    must not show a repo whose summary is still empty.
    """
    if not candidates:
        return []

    by_name = {c["full_name"]: c for c in candidates}
    prompt = RANK_PROMPT_TEMPLATE.format(
        interest=interest,
        pool_size=pool_size,
        summary_count=summary_count,
        criteria=SELECTION_CRITERIA,
        candidates=json.dumps(_compact(candidates), separators=(",", ":")),
    )
    response = client.messages.create(
        model=SEMANTIC_GATE_MODEL,
        max_tokens=2048,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    usage = response.usage
    print(f"  [Rank candidates] {usage.input_tokens} in / {usage.output_tokens} out tokens")
    log_usage("discover:rank", SEMANTIC_GATE_MODEL, usage.input_tokens, usage.output_tokens)
    result = extract_json(response.content[0].text)

    if not isinstance(result, dict):
        return []
    summaries = {
        s["repo"]: s["summary"]
        for s in result.get("summaries", [])
        if isinstance(s, dict) and "repo" in s and "summary" in s
    }

    pool = []
    for name in result.get("ranked", []):
        cand = by_name.get(name)
        if cand is None:  # hallucinated repo — not in the candidate list
            continue
        pool.append(
            {
                "repo": name,
                "summary": summaries.get(name, ""),
                "stars": cand.get("stargazers_count"),
                "language": cand.get("language") or None,
            }
        )
    return pool[:pool_size]


def fill_summaries(interest: str, pool: list[dict], candidates: list[dict]) -> list[dict]:
    """Summaries for the pool entries rank_and_summarize() left blank.

    Runs off the response path, so its latency is invisible to the student.
    Returns the pool with summaries merged in; entries that still fail to get
    one keep summary="" and stay hidden rather than rendering empty.
    """
    missing = [p for p in pool if not p.get("summary")]
    if not missing:
        return pool

    by_name = {c["full_name"]: c for c in candidates}
    to_summarize = [by_name[p["repo"]] for p in missing if p["repo"] in by_name]
    if not to_summarize:
        return pool

    prompt = SUMMARY_ONLY_PROMPT_TEMPLATE.format(
        interest=interest,
        criteria=SELECTION_CRITERIA,
        candidates=json.dumps(_compact(to_summarize), separators=(",", ":")),
    )
    response = client.messages.create(
        model=SEMANTIC_GATE_MODEL,
        max_tokens=2048,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    usage = response.usage
    print(f"  [Fill summaries] {usage.input_tokens} in / {usage.output_tokens} out tokens")
    log_usage("discover:fill", SEMANTIC_GATE_MODEL, usage.input_tokens, usage.output_tokens)

    filled = {e["repo"]: e["summary"] for e in _enrich(extract_json(response.content[0].text), by_name)}
    for entry in pool:
        if not entry.get("summary"):
            entry["summary"] = filled.get(entry["repo"], "")
    return pool
