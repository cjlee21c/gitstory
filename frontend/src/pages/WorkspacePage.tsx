import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getWorkspace } from "../api/client";
import type { WorkspaceContent } from "../api/types";
import { BeatRenderer } from "../components/workspace/BeatRenderer";

export function WorkspacePage() {
  const [params] = useSearchParams();
  const storyId = params.get("story") ?? "";

  const [workspace, setWorkspace] = useState<WorkspaceContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    if (!storyId) return;
    setWorkspace(null);
    setError(null);
    setRevealed(false);
    getWorkspace(storyId)
      .then(setWorkspace)
      .catch((e: Error) => setError(e.message));
  }, [storyId]);

  if (!storyId) {
    return (
      <p className="page">
        No story selected. <a href="/">Go back</a>
      </p>
    );
  }
  if (error) return <p className="page error">{error}</p>;
  if (!workspace) {
    return <p className="page">Generating the workspace for {storyId}... this can take up to a minute the first time.</p>;
  }

  const checkpoint = workspace.beats.find((b) => b.type === "checkpoint");
  const checkpointOrder = checkpoint?.order ?? Infinity;
  const visibleBeats = workspace.beats.filter((b) => revealed || b.order <= checkpointOrder);

  return (
    <div className="page page-narrow workspace">
      {visibleBeats.map((beat) => (
        <BeatRenderer key={beat.beat_id} beat={beat} onCheckpointSubmit={() => setRevealed(true)} />
      ))}
    </div>
  );
}
