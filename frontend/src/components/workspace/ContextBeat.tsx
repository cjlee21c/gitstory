import type { ContextBeat as ContextBeatType } from "../../api/types";

export function ContextBeat({ beat }: { beat: ContextBeatType }) {
  return (
    <section className="beat beat-context">
      <h2>{beat.title}</h2>
      <p>{beat.body}</p>
    </section>
  );
}
