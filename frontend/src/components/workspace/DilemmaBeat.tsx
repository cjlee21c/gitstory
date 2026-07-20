import type { DilemmaBeat as DilemmaBeatType } from "../../api/types";
import { highlightCode } from "./highlight";

export function DilemmaBeat({ beat }: { beat: DilemmaBeatType }) {
  return (
    <section className="beat beat-dilemma">
      <h1>{beat.title}</h1>
      <div className="dilemma-callout">
        <span className="dilemma-flag">⚡ The tension</span>
        <p>{highlightCode(beat.body)}</p>
      </div>
    </section>
  );
}
