import type { DilemmaBeat as DilemmaBeatType } from "../../api/types";

export function DilemmaBeat({ beat }: { beat: DilemmaBeatType }) {
  return (
    <section className="beat beat-dilemma">
      <h1>{beat.title}</h1>
      <div className="dilemma-callout">
        <p>{beat.body}</p>
      </div>
    </section>
  );
}
