from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from app.filters import CONTRIBUTOR_BUCKETS, DOMAINS, SIZE_BUCKETS, STAR_BUCKETS

# Literal types generated from filters.py so an unknown filter id from the
# frontend fails validation with a 422 instead of silently passing through.
DomainId = Literal[tuple(DOMAINS)]  # type: ignore[valid-type]
SizeId = Literal[tuple(SIZE_BUCKETS)]  # type: ignore[valid-type]
StarId = Literal[tuple(STAR_BUCKETS)]  # type: ignore[valid-type]
ContribId = Literal[tuple(CONTRIBUTOR_BUCKETS)]  # type: ignore[valid-type]


class StoryMetadata(BaseModel):
    title: str
    labels: list[str]
    qualities: list[str] = []


class PRMetadata(BaseModel):
    merged_at: str
    reviewers: list[str]
    changed_files: int


class IssuePayload(BaseModel):
    body: str


class DiscussionEntry(BaseModel):
    author: str
    role: str
    body: str
    timestamp: str


class CommitEntry(BaseModel):
    sha: str
    message: str
    author: str
    timestamp: str


class StoryBundle(BaseModel):
    story_id: str
    metadata: StoryMetadata
    pr_metadata: PRMetadata
    issue_payload: IssuePayload
    discussion_timeline: list[DiscussionEntry]
    commit_history: list[CommitEntry]


class StorySummary(BaseModel):
    story_id: str
    title: str
    labels: list[str]
    qualities: list[str] = []


class PipelineRunResponse(BaseModel):
    repo: str
    story_count: int
    cached: bool
    stories: list[StorySummary]


class ContextBeat(BaseModel):
    beat_id: str
    type: Literal["context"]
    order: int
    title: str
    body: str
    source_refs: list[str] = []


class DilemmaBeat(BaseModel):
    beat_id: str
    type: Literal["dilemma"]
    order: int
    title: str
    body: str
    source_refs: list[str] = []


class ViewpointBeat(BaseModel):
    beat_id: str
    type: Literal["viewpoint"]
    order: int
    title: str
    body: str
    author: str
    author_role: str
    source_refs: list[str] = []

class CheckpointBeat(BaseModel):
    beat_id: str
    type: Literal["checkpoint"]
    order: int
    question: str
    format: Literal["reflection"] = "reflection"
    must_precede_decision: bool = True


class DecisionBeat(BaseModel):
    beat_id: str
    type: Literal["decision"]
    order: int
    title: str
    body: str
    source_refs: list[str] = []


class LessonsBeat(BaseModel):
    beat_id: str
    type: Literal["lessons"]
    order: int
    title: str
    lessons: list[str]


Beat = Annotated[
    Union[ContextBeat, DilemmaBeat, ViewpointBeat, CheckpointBeat, DecisionBeat, LessonsBeat],
    Field(discriminator="type"),
]


class WorkspaceContent(BaseModel):
    story_id: str
    beats: list[Beat]


class DiscoverRequest(BaseModel):
    domain: DomainId
    sizes: list[SizeId] = []
    stars: StarId | None = None
    contributors: ContribId | None = None
    keyword: str | None = None


class RepoRecommendation(BaseModel):
    repo: str
    summary: str
