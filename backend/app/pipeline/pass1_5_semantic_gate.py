import time
from concurrent.futures import ThreadPoolExecutor

from app.llm.client import SEMANTIC_GATE_MODEL, client

GATE_PROMPT_TEMPLATE = (
    "Does this open-source discussion contain technical friction, architectural trade-offs, "
    "or design conflicts? Respond strictly with Yes or No.\n\n"
    "Context:\n{context}"
)

MAX_WORKERS = 8


def _gate_candidate(candidate):
    """Runs one Haiku call to judge a single candidate. Independent across
    candidates, so callers can run many of these concurrently. Returns the
    surviving candidate (or None) plus a (input_tokens, output_tokens) tuple
    so the caller can tally token usage without shared mutable state."""
    issue = candidate["issue"]
    comments_snippet = "\n".join(
        f"{c.get('user', {}).get('login', 'unknown')} ({c.get('author_association', 'NONE')}): {c.get('body', '')[:200]}"
        for c in candidate["comments"][:5]
    )
    compact_context = (
        f"Title: {issue['title']}\nBody: {str(issue.get('body', ''))[:400]}\nComments:\n{comments_snippet}"
    )
    prompt = GATE_PROMPT_TEMPLATE.format(context=compact_context)

    try:
        response = client.messages.create(
            model=SEMANTIC_GATE_MODEL,
            max_tokens=10,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        usage = (response.usage.input_tokens, response.usage.output_tokens)
        decision = response.content[0].text.strip()
        if "Yes" in decision:
            print(f"  [Elite] #{issue['number']}: {issue['title'][:50]}")
            return candidate, usage
        print(f"  [Skip] #{issue['number']} lacks technical drama")
        return None, usage
    except Exception as e:
        print(f"  [API Error] #{issue['number']}: {e}")
        return None, (0, 0)


def pass_1_5_semantic_gate(qualified_candidates):
    print("\nInitiating Pass 1.5: Semantic Pre-Screening Gate...")
    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(_gate_candidate, qualified_candidates))

    elite_candidates = [c for c, _ in results if c is not None]
    total_in = sum(usage[0] for _, usage in results)
    total_out = sum(usage[1] for _, usage in results)

    elapsed = round(time.time() - start, 1)
    print(
        f"\nPass 1.5 Complete. {len(elite_candidates)} elite candidates secured. "
        f"({elapsed}s, {total_in} in / {total_out} out tokens)"
    )
    return elite_candidates
