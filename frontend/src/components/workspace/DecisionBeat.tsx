import type { DecisionBeat as DecisionBeatType } from "../../api/types";

export function DecisionBeat({ beat }: { beat: DecisionBeatType }) {
  return (
    <section className="beat beat-decision">
      <span className="badge">What actually happened</span>
      <h2>{beat.title}</h2>
      <p>{beat.body}</p>
    </section>
  );
}
