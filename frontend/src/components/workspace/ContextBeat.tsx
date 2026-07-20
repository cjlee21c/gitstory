import type { ContextBeat as ContextBeatType } from "../../api/types";
import { highlightCode } from "./highlight";

export function ContextBeat({ beat }: { beat: ContextBeatType }) {
  return (
    <section className="beat beat-context">
      <h1>{beat.title}</h1>
      <p>{highlightCode(beat.body)}</p>
    </section>
  );
}
