import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getWorkspacePart } from "../api/client";
import type { Beat, ViewpointBeat, ViewpointOption, WorkspaceContent } from "../api/types";
import { BeatRenderer } from "../components/workspace/BeatRenderer";
import { StoryProgress } from "../components/workspace/StoryProgress";
import { useStudent } from "../context/StudentContext";

const STEP_NAMES = ["Background", "The Problem", "The Debate", "Your Take", "What Happened", "Key Lessons"];

/** Chrome shared by the loading, error and loaded states, so arriving content
 *  swaps into place instead of replacing a whole different-looking page. */
function WorkspaceFrame({
  title,
  onBack,
  children,
}: {
  title: string;
  onBack: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="workspace-shell">
      <header className="workspace-header">
        <div className="workspace-header-top">
          <button className="btn-back" onClick={onBack}>← Back</button>
          <span className="workspace-title">{title}</span>
        </div>
        {/* current=-1 so no step reads as active while there is nothing to read
            yet — the map is still shown, so the reader sees the shape of what's
            coming rather than a blank header. */}
        <StoryProgress steps={STEP_NAMES} current={-1} unlockedUpTo={-1} onNavigate={() => {}} />
      </header>
      <div className="workspace-content">{children}</div>
    </div>
  );
}

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
  // Bumped by Retry to re-run the fetch effect after a failure.
  const [attempt, setAttempt] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!storyId) return;
    const key = `${storyId}#${attempt}`;
    if (fetchedFor.current === key) return;
    fetchedFor.current = key;
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
  }, [storyId, attempt]);

  // Honest elapsed counter while Part 1 generates — a first, uncached run is
  // real Sonnet work and can take the better part of a minute. Showing the
  // seconds tick is the difference between "working" and "frozen".
  const waiting = !!storyId && !part1 && !error;
  useEffect(() => {
    if (!waiting) return;
    setElapsed(0);
    const started = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(id);
  }, [waiting, storyId, attempt]);

  // Keyboard navigation (←/→). Refs keep the listener reading fresh values
  // without re-binding. Space is intentionally left free for scrolling.
  const stepRef = useRef(currentStep);
  stepRef.current = currentStep;
  const doneRef = useRef(checkpointDone);
  doneRef.current = checkpointDone;
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
      const s = stepRef.current;
      const unlocked = doneRef.current ? 5 : 3;
      if (e.key === "ArrowRight" && s < Math.min(5, unlocked)) {
        setCurrentStep(s + 1);
        contentRef.current?.scrollTo({ top: 0 });
      } else if (e.key === "ArrowLeft" && s > 0) {
        setCurrentStep(s - 1);
        contentRef.current?.scrollTo({ top: 0 });
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Until Part 1 lands there is no generated title, so name the story by its
  // repo and PR number rather than showing a bare id.
  const [repoName, prNumber] = storyId.split("#");
  const storyLabel = prNumber ? `${repoName} #${prNumber}` : storyId;

  if (!storyId) {
    return (
      <div className="landing">
        <div className="landing-inner">
          <main className="landing-main">
            <div className="discover-empty">
              <h1>No story selected</h1>
              <p>Head back and pick a story to open its workspace.</p>
              <button className="btn-lg btn-mint" onClick={() => navigate("/")}>
                Back to start <span className="arrow" aria-hidden="true">→</span>
              </button>
            </div>
          </main>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <WorkspaceFrame title={storyLabel} onBack={() => navigate(-1)}>
        <div className="step-card ws-state">
          <p className="step-type-label">Something went wrong</p>
          <h1>We couldn't build this story</h1>
          <p className="ws-state-lead">
            The workspace for <strong>{storyLabel}</strong> failed to generate. Retrying is safe —
            whichever half already generated is reused rather than paid for twice.
          </p>
          <p className="ws-state-detail">{error}</p>
          <div className="ws-state-actions">
            <button
              className="btn-lg btn-mint"
              onClick={() => {
                setError(null);
                setAttempt((n) => n + 1);
              }}
            >
              Try again
            </button>
            <button className="btn-sm ghost" onClick={() => navigate(-1)}>
              Back to stories
            </button>
          </div>
        </div>
      </WorkspaceFrame>
    );
  }

  if (!part1) {
    return (
      <WorkspaceFrame title={storyLabel} onBack={() => navigate(-1)}>
        <div className="step-card ws-state ws-generating">
          <p className="step-type-label">{STEP_NAMES[0]}</p>
          <div className="ws-gen-head">
            <span className="ws-gen-spinner" aria-hidden="true" />
            <div>
              <h1>Writing this story…</h1>
              <p className="ws-state-lead">
                Reading the discussion on <strong>{storyLabel}</strong> — the argument, the code,
                and how it was settled.
              </p>
            </div>
          </div>

          <p className="ws-gen-meta" role="status">
            <span className="ws-gen-elapsed">{elapsed}s</span>
            First run takes around a minute. After that this story opens instantly.
          </p>

          {/* Shaped like the Background step that is about to replace it, so the
              arrival reads as content filling in rather than a page swap. */}
          <div className="ws-skeleton" aria-hidden="true">
            <div className="sk-line sk-title" />
            <div className="sk-line" />
            <div className="sk-line" />
            <div className="sk-line sk-short" />
          </div>
        </div>
      </WorkspaceFrame>
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

      {canGoNext && (
        <div className="kbd-hint">
          Press <kbd>→</kbd> to continue
        </div>
      )}

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
