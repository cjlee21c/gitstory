import json
import time
from concurrent.futures import ThreadPoolExecutor

from app.filters import QUALITY_ATTRIBUTES, QUALITY_DEFINITIONS
from app.llm.client import SEMANTIC_GATE_MODEL, client
from app.llm.json_utils import extract_json
from app.llm.usage import log_usage
from app.pipeline.ranking import stage2_score

_QUALITY_DEFINITIONS_TEXT = "\n".join(
    f"- {name}: {definition}" for name, definition in QUALITY_DEFINITIONS.items()
)

GATE_PROMPT_TEMPLATE = (
    "You are screening an open-source issue discussion.\n\n"
    "Answer two things:\n"
    "1. is_story: does the discussion contain technical friction, architectural "
    "trade-offs, or design conflicts worth studying?\n"
    "2. qualities: which software quality attributes are central to the discussion "
    "(empty list if none clearly apply):\n"
    f"{_QUALITY_DEFINITIONS_TEXT}\n\n"
    "Context:\n{context}"
)

MAX_WORKERS = 16  # per-candidate Haiku calls are independent; more overlap = less wall time
# Generous ceiling: the JSON is ~40 tokens, but output_tokens == max_tokens
# means silent truncation (see the workspace-generator retry bug), so leave room.
GATE_MAX_TOKENS = 300

# Enum generated from QUALITY_ATTRIBUTES so labels can never drift from the
# read-time filter in routes_repos.
GATE_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "is_story": {"type": "boolean"},
        "qualities": {
            "type": "array",
            "items": {"type": "string", "enum": QUALITY_ATTRIBUTES},
        },
    },
    "required": ["is_story", "qualities"],
    "additionalProperties": False,
}


def _parse_gate_response(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        return extract_json(text)
    except Exception:
        # Last resort: salvage the yes/no signal, drop the labels.
        return {"is_story": "true" in text.lower(), "qualities": []}


GATE_EXCERPT_SIZE = 6


def _gate_excerpt(comments: list[dict]) -> list[dict]:
    """Picks which comments the gate reads. Since Pass 1b merges review threads
    into the timeline, the chronological head is often boilerplate ("please
    rebase", CI chatter) while the argument sits deeper in the diff comments.
    Take the longest comments — length is the cheapest available proxy for
    reasoning — then restore chronological order so the exchange still reads as
    a conversation."""
    ranked = sorted(
        enumerate(comments), key=lambda pair: len(pair[1].get("body") or ""), reverse=True
    )
    picked = sorted(ranked[:GATE_EXCERPT_SIZE], key=lambda pair: pair[0])
    return [c for _, c in picked]


def _gate_candidate(candidate):
    """Runs one Haiku call to judge and quality-label a single candidate.
    Independent across candidates, so callers can run many of these
    concurrently. Returns the surviving candidate (or None) plus a
    (input_tokens, output_tokens) tuple so the caller can tally token usage
    without shared mutable state."""
    issue = candidate["issue"]
    comments_snippet = "\n".join(
        f"{c.get('user', {}).get('login', 'unknown')} ({c.get('author_association', 'NONE')}): {c.get('body', '')[:200]}"
        for c in _gate_excerpt(candidate["comments"])
    )
    compact_context = (
        f"Title: {issue['title']}\nBody: {str(issue.get('body', ''))[:400]}\nComments:\n{comments_snippet}"
    )
    prompt = GATE_PROMPT_TEMPLATE.format(context=compact_context)

    try:
        response = client.messages.create(
            model=SEMANTIC_GATE_MODEL,
            max_tokens=GATE_MAX_TOKENS,
            temperature=0,
            output_config={"format": {"type": "json_schema", "schema": GATE_OUTPUT_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        usage = (response.usage.input_tokens, response.usage.output_tokens)
        log_usage(f"gate:#{issue['number']}", SEMANTIC_GATE_MODEL, usage[0], usage[1])
        if response.usage.output_tokens >= GATE_MAX_TOKENS:
            print(f"  [Truncation warning] #{issue['number']} hit max_tokens={GATE_MAX_TOKENS}")
        decision = _parse_gate_response(response.content[0].text)
        if decision.get("is_story"):
            qualities = [q for q in decision.get("qualities", []) if q in QUALITY_ATTRIBUTES]
            candidate["qualities"] = qualities
            print(f"  [Elite] #{issue['number']} {qualities}: {issue['title'][:50]}")
            return candidate, usage
        print(f"  [Skip] #{issue['number']} lacks technical drama")
        return None, usage
    except Exception as e:
        print(f"  [API Error] #{issue['number']}: {e}")
        return None, (0, 0)


def pass_1_5_semantic_gate(qualified_candidates):
    print("\nInitiating Pass 1.5: Semantic Gate + Quality Labeling...")
    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(_gate_candidate, qualified_candidates))

    elite_candidates = [c for c, _ in results if c is not None]
    # Stage-2 ordering: now that bodies are in hand we can rank on substance
    # (long comments, back-and-forth, maintainer involvement) rather than raw
    # volume. This is the order STORY_CAP=4 slices, so it decides what the user
    # actually sees.
    # `signals` is attached by Pass 1, but the gate is also called directly in
    # scripts and on candidates rehydrated from disk, so score defensively —
    # an unranked candidate sorts last rather than crashing the run.
    elite_candidates.sort(
        key=lambda c: -stage2_score(c["signals"]) if c.get("signals") else float("inf")
    )
    total_in = sum(usage[0] for _, usage in results)
    total_out = sum(usage[1] for _, usage in results)

    elapsed = round(time.time() - start, 1)
    print(
        f"\nPass 1.5 Complete. {len(elite_candidates)} elite candidates secured. "
        f"({elapsed}s, {total_in} in / {total_out} out tokens)"
    )
    return elite_candidates
