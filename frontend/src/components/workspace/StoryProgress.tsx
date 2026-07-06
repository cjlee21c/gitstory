interface Props {
  steps: string[];
  current: number;
  unlockedUpTo: number;
  onNavigate: (index: number) => void;
}

export function StoryProgress({ steps, current, unlockedUpTo, onNavigate }: Props) {
  return (
    <div className="story-progress">
      <div className="progress-track">
        {steps.map((label, i) => {
          const isCompleted = i < current;
          const isActive = i === current;
          const isLocked = i > unlockedUpTo;

          const dotClass = isLocked
            ? "locked"
            : isCompleted
            ? "completed"
            : isActive
            ? "active"
            : "upcoming";

          const labelClass = isActive
            ? "active-label"
            : isCompleted
            ? "completed-label"
            : "";

          return (
            <div key={i} className="progress-step">
              <button
                className={`progress-dot ${dotClass}`}
                onClick={() => !isLocked && onNavigate(i)}
                disabled={isLocked}
                aria-label={`Step ${i + 1}: ${label}`}
                aria-current={isActive ? "step" : undefined}
              />
              <span className={`progress-label ${labelClass}`}>{label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
