import type { RepoRecommendation } from "../api/types";

interface Props {
  repo: RepoRecommendation;
  selected: boolean;
  disabled: boolean;
  onToggle: () => void;
}

export function RepoCard({ repo, selected, disabled, onToggle }: Props) {
  return (
    <div
      className={`card card-clickable${selected ? " card-selected" : ""}${disabled ? " card-disabled" : ""}`}
      onClick={() => !disabled && onToggle()}
      role="checkbox"
      aria-checked={selected}
      tabIndex={0}
    >
      <label className="checkbox-option" onClick={(e) => e.stopPropagation()}>
        <input type="checkbox" checked={selected} disabled={disabled} onChange={onToggle} />
        <h3>{repo.repo}</h3>
      </label>
      <p>{repo.summary}</p>
    </div>
  );
}
