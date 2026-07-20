import json

from app.filters import DOMAINS
from app.llm.client import SEMANTIC_GATE_MODEL, client
from app.llm.json_utils import extract_json
from app.llm.usage import log_usage

_VALID_DOMAINS = set(DOMAINS)

CLASSIFY_PROMPT = """Classify each GitHub repository into EXACTLY ONE domain id from this list:
{domain_list}

Judge from the repo's owner/name and the titles of its engineering stories. Pick the single
best-fitting domain; if nothing fits well, use "developer_tools".

Respond with ONLY a JSON object mapping "<owner>/<name>" to a domain id — no commentary:
{{"owner/name": "gaming", ...}}

REPOSITORIES:
{repos}
"""


def classify_repos_domains(repos: list[dict]) -> dict[str, str]:
    """Map each repo to one domain id via a single batched Haiku call.

    Storage-agnostic: takes ``[{"repo": "owner/name", "titles": [...]}, ...]`` and returns
    ``{repo: domain_id}`` for the repos it could confidently classify. Callers own caching /
    persistence, so this ports unchanged when the library moves to a database.
    """
    if not repos:
        return {}

    domain_list = "\n".join(f"- {domain_id}: {meta['label']}" for domain_id, meta in DOMAINS.items())
    compact = [{"repo": r["repo"], "stories": (r.get("titles") or [])[:4]} for r in repos]
    prompt = CLASSIFY_PROMPT.format(
        domain_list=domain_list,
        repos=json.dumps(compact, ensure_ascii=False),
    )

    response = client.messages.create(
        model=SEMANTIC_GATE_MODEL,
        max_tokens=1024,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    usage = response.usage
    log_usage("library:classify", SEMANTIC_GATE_MODEL, usage.input_tokens, usage.output_tokens)

    parsed = extract_json(response.content[0].text)
    if not isinstance(parsed, dict):
        return {}
    return {repo: dom for repo, dom in parsed.items() if dom in _VALID_DOMAINS}
