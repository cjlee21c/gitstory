import type { ViewpointBeat as ViewpointBeatType } from "../../api/types";
import { highlightCode } from "./highlight";

// GitHub roles that mean "the project's own people" → maintainer tone; anyone
// else (contributor, none, first-timer…) → contributor tone.
function roleTone(role: string): string {
  return /owner|member|collaborator|maintain/i.test(role) ? "role-maintainer" : "role-contributor";
}

export function ViewpointBeat({ beat }: { beat: ViewpointBeatType }) {
  return (
    <section className="beat beat-viewpoint">
      <img
        className="avatar"
        src={`https://github.com/${beat.author}.png?size=48`}
        alt={beat.author}
        onError={(e) => {
          (e.target as HTMLImageElement).style.display = "none";
        }}
      />
      <div className="bubble-content">
        <div className="bubble-header">
          <span className="bubble-author">{beat.author}</span>
          <span className={`role-badge ${roleTone(beat.author_role)}`}>{beat.author_role}</span>
        </div>
        <p className="bubble-body">{highlightCode(beat.body)}</p>
      </div>
    </section>
  );
}
