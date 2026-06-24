import type { DilemmaBeat as DilemmaBeatType } from "../../api/types";

export function DilemmaBeat({ beat }: { beat: DilemmaBeatType }) {
  return (
    <section className="beat beat-dilemma">
      <h2>{beat.title}</h2>
      <p>{beat.body}</p>
    </section>
  );
}
