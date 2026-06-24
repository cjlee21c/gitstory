import type { ViewpointBeat as ViewpointBeatType } from "../../api/types";

export function ViewpointBeat({ beat }: { beat: ViewpointBeatType }) {
  return (
    <section className="beat beat-viewpoint">
      <h2>{beat.title}</h2>
      <p className="byline">
        {beat.author} <span className="role">({beat.author_role})</span>
      </p>
      <p>{beat.body}</p>
    </section>
  );
}
