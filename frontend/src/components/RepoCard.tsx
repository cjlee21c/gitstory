import type { RepoRecommendation } from "../api/types";

interface Props {
  repo: RepoRecommendation;
  selected: boolean;
  disabled: boolean;
  onToggle: () => void;
}

function formatStars(n: number): string {
  if (n >= 1000) {
    const k = n / 1000;
    return `${k >= 10 ? Math.round(k) : k.toFixed(1).replace(/\.0$/, "")}k`;
  }
  return String(n);
}

export function RepoCard({ repo, selected, disabled, onToggle }: Props) {
  function handleKeyDown(e: React.KeyboardEvent) {
    if (disabled) return;
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      onToggle();
    }
  }

  return (
    <div
      className={`repo-card${selected ? " selected" : ""}${disabled ? " disabled" : ""}`}
      onClick={() => !disabled && onToggle()}
      onKeyDown={handleKeyDown}
      role="checkbox"
      aria-checked={selected}
      aria-disabled={disabled}
      tabIndex={disabled ? -1 : 0}
    >
      <span className="repo-check" aria-hidden={!selected}>✓</span>

      <div className="repo-card-head">
        <svg className="repo-ghico" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path d="M8 0a8 8 0 0 0-2.5 15.6c.4.1.5-.2.5-.4v-1.4c-2 .4-2.5-.5-2.7-1-.1-.3-.5-1-.9-1.2-.3-.2-.7-.6 0-.6.6 0 1 .6 1.2.8.7 1.2 1.9.9 2.3.7.1-.5.3-.9.5-1.1-1.8-.2-3.6-.9-3.6-4 0-.9.3-1.6.8-2.1-.1-.2-.4-1 .1-2.1 0 0 .7-.2 2.2.8a7.4 7.4 0 0 1 4 0c1.5-1 2.2-.8 2.2-.8.5 1.1.2 1.9.1 2.1.5.5.8 1.2.8 2.1 0 3.1-1.8 3.8-3.6 4 .3.3.6.8.6 1.6v2.3c0 .2.1.5.5.4A8 8 0 0 0 8 0Z"/>
        </svg>
        <h3 className="repo-name">{repo.repo}</h3>
      </div>

      {(repo.language || typeof repo.stars === "number") && (
        <div className="repo-meta">
          {repo.language && <span className="repo-tag">{repo.language}</span>}
          {typeof repo.stars === "number" && (
            <span className="repo-tag">⭐ {formatStars(repo.stars)}</span>
          )}
        </div>
      )}

      <p className="repo-summary">{repo.summary}</p>
    </div>
  );
}
