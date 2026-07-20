import type { DecisionBeat as DecisionBeatType } from "../../api/types";
import { highlightCode } from "./highlight";

export function DecisionBeat({ beat }: { beat: DecisionBeatType }) {
  return (
    <section className="beat beat-decision">
      <div className="decision-reveal-banner">✓ What actually happened</div>
      <h1>{beat.title}</h1>
      <p>{highlightCode(beat.body)}</p>
    </section>
  );
}
