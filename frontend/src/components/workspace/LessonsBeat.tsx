import type { LessonsBeat as LessonsBeatType } from "../../api/types";
import { highlightCode } from "./highlight";

export function LessonsBeat({ beat }: { beat: LessonsBeatType }) {
  return (
    <section className="beat beat-lessons">
      <h1>{beat.title}</h1>
      <ol className="lessons-list">
        {beat.lessons.map((lesson, i) => (
          <li key={i}>
            <span className="lesson-number">{String(i + 1).padStart(2, "0")}</span>
            <span>{highlightCode(lesson)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
