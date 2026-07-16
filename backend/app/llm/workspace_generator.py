import json

from pydantic import ValidationError

from app.llm.client import WORKSPACE_GEN_MODEL, client
from app.llm.json_utils import extract_json
from app.llm.usage import log_usage
from app.models.schemas import WorkspaceContent

MAX_ATTEMPTS = 3
COMMENT_BODY_LIMIT = 500
DISCUSSION_COMMENT_CAP = 15

# Part 1 = the run-up the student reads BEFORE forming a judgment: context, the
# dilemma, the real opposing viewpoints, and the reflection checkpoint. This is
# what gates the initial wait, so it is generated and returned first.
PART1_PROMPT_TEMPLATE = """You are turning a real, closed-source-free software engineering discussion into educational content for students learning architectural decision-making. You are given the raw discussion data below for story_id "{story_id}".

Your task: produce a single JSON object with the OPENING beats that let a student walk through the REAL discussion and form their own judgment. Do NOT reveal or hint at the final outcome — that is deliberately withheld for a later step.

Required JSON shape (return exactly these beat "type" values, in this order):
{{
  "story_id": "{story_id}",
  "beats": [
    {{"beat_id": "b1", "type": "context", "order": 1, "title": "...", "body": "...", "source_refs": ["issue_payload.body"]}},
    {{"beat_id": "b2", "type": "dilemma", "order": 2, "title": "...", "body": "...", "source_refs": [...]}},
    {{"beat_id": "b3", "type": "viewpoint", "order": 3, "title": "Position A — <real github login>", "body": "...", "author": "<login>", "author_role": "<association from data>", "source_refs": [...]}},
    {{"beat_id": "b4", "type": "viewpoint", "order": 4, "title": "Position B — <real github login>", "body": "...", "author": "<login>", "author_role": "<association>", "source_refs": [...]}},
    {{"beat_id": "b5", "type": "checkpoint", "order": 5, "question": "...", "format": "reflection", "must_precede_decision": true}}
  ]
}}

Rules:
- BE CONCISE. Every "body" must be at most 3 sentences (~60 words). Every "question" is one sentence (~30 words). Pack meaning densely; never pad, repeat, or restate. Brevity is a hard requirement, not a preference.
- Use 2-3 "viewpoint" beats representing REAL, DISTINCT positions actually argued by REAL participants in the data. Use their actual GitHub logins and author_association values. Never invent a person or a position nobody took.
- The "checkpoint" question asks the student what THEY would decide. It MUST NOT reveal, assume, or hint at the actual outcome.
- NEVER mention specific code, diffs, syntax, file names, or line numbers anywhere. Describe the engineering tradeoffs, reasoning, and arguments only, in plain prose.
- "source_refs" should name which raw fields informed that beat, e.g. "discussion_timeline[3]", "issue_payload.body".
- Output ONLY the JSON object. No markdown code fences, no commentary before or after.

RAW DATA:
{raw_data}
"""

# Part 2 = the payoff the student only unlocks after the checkpoint: what
# actually happened and the lessons. Generated separately so its latency hides
# behind the time the student spends reading Part 1.
PART2_PROMPT_TEMPLATE = """You are turning a real, closed-source-free software engineering discussion into educational content for students learning architectural decision-making. You are given the raw discussion data below for story_id "{story_id}".

Your task: produce a single JSON object with the CLOSING beats — what the team ACTUALLY decided, and the engineering lessons. The student has already read the context, the dilemma, the opposing viewpoints, and answered a reflection checkpoint; now reveal the outcome.

Required JSON shape (return exactly these beat "type" values, in this order):
{{
  "story_id": "{story_id}",
  "beats": [
    {{"beat_id": "b6", "type": "decision", "order": 6, "title": "...", "body": "...", "source_refs": [...]}},
    {{"beat_id": "b7", "type": "lessons", "order": 7, "title": "Engineering Lessons", "lessons": ["...", "...", "..."]}}
  ]
}}

Rules:
- BE CONCISE. The "body" must be at most 3 sentences (~60 words). Each item in "lessons" is one sentence (~20 words). Pack meaning densely; never pad, repeat, or restate. Brevity is a hard requirement, not a preference.
- The "decision" beat must accurately describe what ACTUALLY happened — cross-check against commit_history and pr_metadata.merged_at. Do not invent an outcome.
- Provide exactly 3 "lessons".
- NEVER mention specific code, diffs, syntax, file names, or line numbers anywhere. Describe the engineering tradeoffs, reasoning, and arguments only, in plain prose.
- "source_refs" should name which raw fields informed that beat, e.g. "commit_history", "discussion_timeline[3]".
- Output ONLY the JSON object. No markdown code fences, no commentary before or after.

RAW DATA:
{raw_data}
"""

RETRY_SUFFIX = (
    "\n\nYour previous response was rejected for this reason: {error}\n"
    "Return ONLY a corrected, valid JSON object matching the required shape."
)


def _truncate(text: str, limit: int = COMMENT_BODY_LIMIT) -> str:
    if not text or len(text) <= limit:
        return text
    return text[:limit] + "... [truncated]"


def _sample_comments(comments: list, cap: int = DISCUSSION_COMMENT_CAP) -> list:
    if len(comments) <= cap:
        return comments
    # Take spread across the discussion arc: start, middle, end
    step = (len(comments) - 1) / (cap - 1)
    indices = sorted({round(i * step) for i in range(cap)})
    return [comments[i] for i in indices]


def _build_raw_data(bundle: dict) -> str:
    sampled = _sample_comments(bundle["discussion_timeline"])
    compact = {
        "metadata": bundle["metadata"],
        "pr_metadata": bundle["pr_metadata"],
        "issue_payload": {"body": _truncate(bundle["issue_payload"]["body"])},
        "discussion_timeline": [
            {**entry, "body": _truncate(entry["body"])} for entry in sampled
        ],
        "commit_history": bundle["commit_history"],
    }
    # Compact separators (no indent whitespace) to cut input tokens — the model
    # doesn't need pretty-printed JSON.
    return json.dumps(compact, separators=(",", ":"), ensure_ascii=False)


def _require_beat(workspace: WorkspaceContent, beat_type: str) -> None:
    if not any(b.type == beat_type for b in workspace.beats):
        raise ValueError(f"workspace is missing a {beat_type} beat")


def _generate(bundle: dict, prompt_template: str, phase: str, required_beat: str) -> WorkspaceContent:
    story_id = bundle["story_id"]
    prompt = prompt_template.format(story_id=story_id, raw_data=_build_raw_data(bundle))

    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        message = prompt if attempt == 0 else prompt + RETRY_SUFFIX.format(error=last_error)
        response = client.messages.create(
            model=WORKSPACE_GEN_MODEL,
            max_tokens=4000,
            temperature=0,
            messages=[{"role": "user", "content": message}],
        )
        usage = response.usage
        print(
            f"  [Workspace {story_id} {phase}] attempt {attempt + 1}: "
            f"{usage.input_tokens} in / {usage.output_tokens} out tokens"
        )
        log_usage(
            f"workspace:{story_id}:{phase}", WORKSPACE_GEN_MODEL,
            usage.input_tokens, usage.output_tokens, attempt=attempt + 1,
        )
        raw_text = response.content[0].text
        try:
            data = extract_json(raw_text)
            workspace = WorkspaceContent.model_validate(data)
            _require_beat(workspace, required_beat)
            return workspace
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            last_error = str(e)
            continue

    raise RuntimeError(
        f"Failed to generate valid workspace {phase} for {story_id} after {MAX_ATTEMPTS} attempts: {last_error}"
    )


def generate_workspace_part1(bundle: dict) -> WorkspaceContent:
    """Opening beats (context, dilemma, viewpoints, checkpoint) — returned first."""
    return _generate(bundle, PART1_PROMPT_TEMPLATE, "p1", "checkpoint")


def generate_workspace_part2(bundle: dict) -> WorkspaceContent:
    """Closing beats (decision, lessons) — generated behind the checkpoint gate."""
    return _generate(bundle, PART2_PROMPT_TEMPLATE, "p2", "decision")


def generate_workspace(bundle: dict) -> WorkspaceContent:
    """Full workspace, both phases merged. Kept for the no-`part` endpoint and any
    caller that wants everything in one object; the frontend fetches the two parts
    separately so Part 2's latency hides behind reading Part 1."""
    part1 = generate_workspace_part1(bundle)
    part2 = generate_workspace_part2(bundle)
    return WorkspaceContent(story_id=bundle["story_id"], beats=[*part1.beats, *part2.beats])
