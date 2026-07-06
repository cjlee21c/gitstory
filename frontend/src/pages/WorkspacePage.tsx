import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getWorkspace } from "../api/client";
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

  const [workspace, setWorkspace] = useState<WorkspaceContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [checkpointDone, setCheckpointDone] = useState(false);

  useEffect(() => {
    if (!storyId) return;
    setWorkspace(null);
    setError(null);
    setCurrentStep(0);
    setCheckpointDone(false);
    getWorkspace(storyId)
      .then(setWorkspace)
      .catch((e: Error) => setError(e.message));
  }, [storyId]);

  if (!storyId) {
    return <p className="page">No story selected. <a href="/">Go back</a></p>;
  }
  if (error) return <p className="page error">{error}</p>;
  if (!workspace) {
    return (
      <p className="page">
        Generating workspace for {storyId}… this can take up to a minute the first time.
      </p>
    );
  }

  const groups = groupBeats(workspace.beats);
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
          {currentBeats.length === 0 ? (
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
