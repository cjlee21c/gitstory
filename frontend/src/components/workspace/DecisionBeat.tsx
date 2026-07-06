import type { DecisionBeat as DecisionBeatType } from "../../api/types";

export function DecisionBeat({ beat }: { beat: DecisionBeatType }) {
  return (
    <section className="beat beat-decision">
      <div className="decision-reveal-banner">✓ What actually happened</div>
      <h1>{beat.title}</h1>
      <p>{beat.body}</p>
    </section>
  );
}
