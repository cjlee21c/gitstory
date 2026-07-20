import type { StorySummary } from "../api/types";

interface Props {
  story: StorySummary;
  onOpen: () => void;
  repoBadge?: string;
}

// Fixed semantic tones for the 4 controlled qualities; anything else is neutral.
const QUALITY_TONE: Record<string, string> = {
  security: "tag-security",
  performance: "tag-performance",
  usability: "tag-usability",
  maintainability: "tag-maintainability",
};

export function StoryCard({ story, onOpen, repoBadge }: Props) {
  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      onOpen();
    }
  }

  return (
    <div
      className="story-card"
      onClick={onOpen}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
    >
      {repoBadge && <span className="story-repo-badge">{repoBadge}</span>}
      <h3 className="story-title">{story.title}</h3>

      {(story.qualities.length > 0 || story.labels.length > 0) && (
        <div className="story-tags">
          {story.qualities.map((quality) => (
            <span key={quality} className={`tag ${QUALITY_TONE[quality] ?? "tag-neutral"}`}>
              {quality}
            </span>
          ))}
          {story.labels.map((label) => (
            <span key={label} className="tag tag-neutral">
              {label}
            </span>
          ))}
        </div>
      )}

      <div className="story-card-foot">
        <span className="story-cta">
          Start Story <span className="arrow" aria-hidden="true">→</span>
        </span>
      </div>
    </div>
  );
}
