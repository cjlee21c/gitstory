import type { ViewpointBeat as ViewpointBeatType } from "../../api/types";
import { highlightCode } from "./highlight";

// GitHub roles that mean "the project's own people" → maintainer tone; anyone
// else (contributor, none, first-timer…) → contributor tone.
function roleTone(role: string): string {
  return /owner|member|collaborator|maintain/i.test(role) ? "role-maintainer" : "role-contributor";
}

// Participants reach the page pseudonymized ("Maintainer A", "Outside
// Commenter B"), so initials are all an avatar can show — and all it should.
// This used to load https://github.com/<login>.png, which put a real
// contributor's face on screen and told GitHub which of them a student was
// reading about.
function initials(alias: string): string {
  return alias
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word[0])
    .join("")
    .slice(0, 3)
    .toUpperCase();
}

export function ViewpointBeat({ beat }: { beat: ViewpointBeatType }) {
  const tone = roleTone(beat.author_role);
  return (
    <section className="beat beat-viewpoint">
      <div className={`avatar avatar-alias ${tone}`} aria-hidden="true">
        {initials(beat.author)}
      </div>
      <div className="bubble-content">
        <div className="bubble-header">
          <span className="bubble-author">{beat.author}</span>
          <span className={`role-badge ${tone}`}>{beat.author_role}</span>
        </div>
        <p className="bubble-body">{highlightCode(beat.body)}</p>
      </div>
    </section>
  );
}
