import type { StorySummary } from "../api/types";

interface Props {
  story: StorySummary;
  onOpen: () => void;
  repoBadge?: string;
}

export function StoryCard({ story, onOpen, repoBadge }: Props) {
  return (
    <div className="card card-clickable" onClick={onOpen} role="button" tabIndex={0}>
      {repoBadge && <span className="repo-badge">{repoBadge}</span>}
      <h3>{story.title}</h3>
      <div className="labels">
        {story.qualities.map((quality) => (
          <span key={quality} className="label label-quality">
            {quality}
          </span>
        ))}
        {story.labels.map((label) => (
          <span key={label} className="label">
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
