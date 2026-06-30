import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getLibrary } from "../api/client";
import type { LibraryEntry } from "../api/types";

export function LibraryPage() {
  const [entries, setEntries] = useState<LibraryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getLibrary()
      .then(setEntries)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="page">Loading library...</p>;
  if (error) return <p className="page error">{error}</p>;
  if (entries.length === 0)
    return (
      <p className="page">
        No repos in the library yet. Run the pipeline on a repo first.{" "}
        <a href="/">Go back</a>
      </p>
    );

  return (
    <div className="page">
      <h1>Story Library</h1>
      <p>
        These repos have been pre-processed. Click one to read its stories
        instantly. <a href="/">← Back</a>
      </p>

      {entries.map((entry) => (
        <div key={entry.repo} className="repo-card">
          <h2>{entry.repo}</h2>
          <p>{entry.stories.length} stor{entry.stories.length === 1 ? "y" : "ies"}</p>
          <div className="story-list">
            {entry.stories.map((story) => (
              <div key={story.story_id} className="story-row">
                <button
                  className="story-link"
                  onClick={() =>
                    navigate(`/stories?repo=${encodeURIComponent(entry.repo)}`)
                  }
                >
                  {story.title}
                </button>
                <div className="labels">
                  {story.labels.map((l) => (
                    <span key={l} className="label">
                      {l}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
