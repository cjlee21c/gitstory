import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getWorkspacePart } from "../api/client";
import type { Beat, ViewpointBeat, ViewpointOption, WorkspaceContent } from "../api/types";
import { BeatRenderer } from "../components/workspace/BeatRenderer";
import { StoryProgress } from "../components/workspace/StoryProgress";
import { useStudent } from "../context/StudentContext";

const STEP_NAMES = ["Background", "The Problem", "The Debate", "Your Take", "What Happened", "Key Lessons"];

function groupBeats(beats: Beat[]): Beat[][] {
  const buckets: Beat[][] = [[], [], [], [], [], []];
  for (const beat of beats) {
    switch (beat.type) {
      case "context":    buckets[0].push(beat); break;
      case "dilemma":   buckets[1].push(beat); break;
      case "viewpoint": buckets[2].push(beat); break;
      case "checkpoint": buckets[3].push(beat); break;
      case "decision":  buckets[4].push(beat); break;
      case "lessons":   buckets[5].push(beat); break;
    }
  }
  return buckets;
}

export function WorkspacePage() {
  const [params] = useSearchParams();
  const storyId = params.get("story") ?? "";
  const { studentId } = useStudent();
  const navigate = useNavigate();
  const contentRef = useRef<HTMLDivElement>(null);
  // Guards against StrictMode's double-effect firing two workspace fetches for
  // the same story — the first (uncached) generation is expensive Sonnet work.
  const fetchedFor = useRef<string | null>(null);

  // Part 1 = opening beats (steps 0-3), awaited before we render. Part 2 =
  // decision + lessons (steps 4-5), fetched in parallel; the user can't reach
  // those steps until they pass the checkpoint, so Part 2's latency is hidden.
  const [part1, setPart1] = useState<WorkspaceContent | null>(null);
  const [part2, setPart2] = useState<WorkspaceContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [part2Error, setPart2Error] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [checkpointDone, setCheckpointDone] = useState(false);

  useEffect(() => {
    if (!storyId) return;
    if (fetchedFor.current === storyId) return;
    fetchedFor.current = storyId;
    setPart1(null);
    setPart2(null);
    setError(null);
    setPart2Error(null);
    setCurrentStep(0);
    setCheckpointDone(false);
    getWorkspacePart(storyId, 1)
      .then(setPart1)
      .catch((e: Error) => setError(e.message));
    getWorkspacePart(storyId, 2)
      .then(setPart2)
      .catch((e: Error) => setPart2Error(e.message));
  }, [storyId]);

  if (!storyId) {
    return <p className="page">No story selected. <a href="/">Go back</a></p>;
  }
  if (error) return <p className="page error">{error}</p>;
  if (!part1) {
    return (
      <p className="page">
        Generating workspace for {storyId}… this can take up to a minute the first time.
      </p>
    );
  }

  const beats = [...part1.beats, ...(part2?.beats ?? [])];
  const workspace: WorkspaceContent = { story_id: storyId, beats };
  const groups = groupBeats(beats);
  const unlockedUpTo = checkpointDone ? 5 : 3;
  const isLastStep = currentStep === 5;
  const canGoNext = !isLastStep && !(currentStep === 3 && !checkpointDone);

  const viewpointOptions: ViewpointOption[] = workspace.beats
    .filter((b): b is ViewpointBeat => b.type === "viewpoint")
    .map((b) => ({ author: b.author, title: b.title }));

  const storyTitle = (workspace.beats.find(b => b.type === "context") as any)?.title ?? storyId;

  function goTo(step: number) {
    if (step < 0 || step > 5 || step > unlockedUpTo) return;
    setCurrentStep(step);
    contentRef.current?.scrollTo({ top: 0 });
  }

  function handleCheckpointSubmit() {
    setCheckpointDone(true);
    setTimeout(() => goTo(4), 0);
  }

  const currentBeats = groups[currentStep];

  return (
    <div className="workspace-shell">
      <header className="workspace-header">
        <div className="workspace-header-top">
          <button className="btn-back" onClick={() => navigate(-1)}>← Back</button>
          <span className="workspace-title">{storyTitle}</span>
        </div>
        <StoryProgress
          steps={STEP_NAMES}
          current={currentStep}
          unlockedUpTo={unlockedUpTo}
          onNavigate={goTo}
        />
      </header>

      <div className="workspace-content" ref={contentRef}>
        <div className="step-card">
          <p className="step-type-label">{STEP_NAMES[currentStep]}</p>
          {currentBeats.length === 0 && currentStep >= 4 && part2Error ? (
            <p className="error">{part2Error}</p>
          ) : currentBeats.length === 0 && currentStep >= 4 && !part2 ? (
            <p style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
              Revealing what happened next…
            </p>
          ) : currentBeats.length === 0 ? (
            <p style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
              No content for this step.
            </p>
          ) : (
            currentBeats.map((beat) => (
              <BeatRenderer
                key={beat.beat_id}
                beat={beat}
                storyId={storyId}
                studentId={studentId}
                viewpointOptions={viewpointOptions}
                onCheckpointSubmit={handleCheckpointSubmit}
              />
            ))
          )}
        </div>
      </div>

      <footer className="workspace-footer">
        <button
          className="btn-prev"
          onClick={() => goTo(currentStep - 1)}
          disabled={currentStep === 0}
        >
          ← Previous
        </button>
        <span className="step-counter">Step {currentStep + 1} of 6</span>
        <button
          className="btn-next"
          onClick={() => isLastStep ? navigate(-1) : goTo(currentStep + 1)}
          disabled={!canGoNext && !isLastStep}
        >
          {isLastStep ? "Finish ✓" : "Next →"}
        </button>
      </footer>
    </div>
  );
}
