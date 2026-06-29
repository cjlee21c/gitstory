import json

from pydantic import ValidationError

from app.llm.client import WORKSPACE_GEN_MODEL, client
from app.llm.json_utils import extract_json
from app.models.schemas import WorkspaceContent

MAX_ATTEMPTS = 3
COMMENT_BODY_LIMIT = 500
DISCUSSION_COMMENT_CAP = 15

PROMPT_TEMPLATE = """You are turning a real, closed-source-free software engineering discussion into educational content for students learning architectural decision-making. You are given the raw discussion data below for story_id "{story_id}".

Your task: produce a single JSON object describing an ordered sequence of "beats" that lets a student walk through the REAL discussion and form their own judgment BEFORE the actual decision is revealed.

Required JSON shape (return exactly these beat "type" values, in this rough order):
{{
  "story_id": "{story_id}",
  "beats": [
    {{"beat_id": "b1", "type": "context", "order": 1, "title": "...", "body": "...", "source_refs": ["issue_payload.body"]}},
    {{"beat_id": "b2", "type": "dilemma", "order": 2, "title": "...", "body": "...", "source_refs": [...]}},
    {{"beat_id": "b3", "type": "viewpoint", "order": 3, "title": "Position A — <real github login>", "body": "...", "author": "<login>", "author_role": "<association from data>", "source_refs": [...]}},
    {{"beat_id": "b4", "type": "viewpoint", "order": 4, "title": "Position B — <real github login>", "body": "...", "author": "<login>", "author_role": "<association>", "source_refs": [...]}},
    {{"beat_id": "b5", "type": "checkpoint", "order": 5, "question": "...", "format": "reflection", "must_precede_decision": true}},
    {{"beat_id": "b6", "type": "decision", "order": 6, "title": "...", "body": "...", "source_refs": [...]}},
    {{"beat_id": "b7", "type": "lessons", "order": 7, "title": "Engineering Lessons", "lessons": ["...", "...", "..."]}}
  ]
}}

Rules:
- Use 2-3 "viewpoint" beats representing REAL, DISTINCT positions actually argued by REAL participants in the data. Use their actual GitHub logins and author_association values. Never invent a person or a position nobody took.
- The "checkpoint" beat's order MUST be strictly less than the "decision" beat's order.
- The "decision" beat must accurately describe what ACTUALLY happened — cross-check against commit_history and pr_metadata.merged_at. Do not invent an outcome.
- NEVER mention specific code, diffs, syntax, file names, or line numbers anywhere. Describe the engineering tradeoffs, reasoning, and arguments only, in plain prose.
- "source_refs" should name which raw fields informed that beat, e.g. "discussion_timeline[3]", "issue_payload.body", "commit_history".
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
    return json.dumps(compact, indent=2, ensure_ascii=False)


def _validate_checkpoint_precedes_decision(workspace: WorkspaceContent) -> None:
    checkpoint_orders = [b.order for b in workspace.beats if b.type == "checkpoint"]
    decision_orders = [b.order for b in workspace.beats if b.type == "decision"]
    if not checkpoint_orders:
        raise ValueError("workspace is missing a checkpoint beat")
    if not decision_orders:
        raise ValueError("workspace is missing a decision beat")
    if max(checkpoint_orders) >= min(decision_orders):
        raise ValueError("checkpoint beat order must be strictly less than decision beat order")


def generate_workspace(bundle: dict) -> WorkspaceContent:
    story_id = bundle["story_id"]
    prompt = PROMPT_TEMPLATE.format(story_id=story_id, raw_data=_build_raw_data(bundle))

    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        message = prompt if attempt == 0 else prompt + RETRY_SUFFIX.format(error=last_error)
        response = client.messages.create(
            model=WORKSPACE_GEN_MODEL,
            max_tokens=1800,
            temperature=0,
            messages=[{"role": "user", "content": message}],
        )
        raw_text = response.content[0].text
        try:
            data = extract_json(raw_text)
            workspace = WorkspaceContent.model_validate(data)
            _validate_checkpoint_precedes_decision(workspace)
            return workspace
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            last_error = str(e)
            continue

    raise RuntimeError(
        f"Failed to generate valid workspace content for {story_id} after {MAX_ATTEMPTS} attempts: {last_error}"
    )
