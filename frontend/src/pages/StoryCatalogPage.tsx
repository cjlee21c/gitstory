import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { listStories } from "../api/client";
import type { StorySummary } from "../api/types";
import { StoryCard } from "../components/StoryCard";

export function StoryCatalogPage() {
  const [params] = useSearchParams();
  const repo = params.get("repo") ?? "";
  const navigate = useNavigate();

  const [stories, setStories] = useState<StorySummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!repo) return;
    setStories(null);
    setError(null);
    listStories(repo)
      .then(setStories)
      .catch((e: Error) => setError(e.message));
  }, [repo]);

  if (!repo) {
    return (
      <p className="page">
        No repo selected. <a href="/">Go back</a>
      </p>
    );
  }
  if (error) return <p className="page error">{error}</p>;
  if (!stories) return <p className="page">Loading stories for {repo}...</p>;

  return (
    <div className="page">
      <h1>{repo}</h1>
      <p>{stories.length} engineering stories found</p>
      <div className="grid">
        {stories.map((s) => (
          <StoryCard
            key={s.story_id}
            story={s}
            onOpen={() => navigate(`/workspace?story=${encodeURIComponent(s.story_id)}`)}
          />
        ))}
      </div>
    </div>
  );
}
