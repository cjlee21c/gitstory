import type { StorySummary } from "../api/types";

interface Props {
  story: StorySummary;
  onOpen: () => void;
}

export function StoryCard({ story, onOpen }: Props) {
  return (
    <div className="card card-clickable" onClick={onOpen} role="button" tabIndex={0}>
      <h3>{story.title}</h3>
      <div className="labels">
        {story.labels.map((label) => (
          <span key={label} className="label">
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
