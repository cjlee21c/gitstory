import type { ContextBeat as ContextBeatType } from "../../api/types";

export function ContextBeat({ beat }: { beat: ContextBeatType }) {
  return (
    <section className="beat beat-context">
      <h1>{beat.title}</h1>
      <p>{beat.body}</p>
    </section>
  );
}
