import type { LessonsBeat as LessonsBeatType } from "../../api/types";

export function LessonsBeat({ beat }: { beat: LessonsBeatType }) {
  return (
    <section className="beat beat-lessons">
      <h2>{beat.title}</h2>
      <ul>
        {beat.lessons.map((lesson, i) => (
          <li key={i}>{lesson}</li>
        ))}
      </ul>
    </section>
  );
}
