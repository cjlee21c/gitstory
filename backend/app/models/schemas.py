from pydantic import BaseModel


class StoryMetadata(BaseModel):
    title: str
    labels: list[str]


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


class PipelineRunResponse(BaseModel):
    repo: str
    story_count: int
    cached: bool
    stories: list[StorySummary]
