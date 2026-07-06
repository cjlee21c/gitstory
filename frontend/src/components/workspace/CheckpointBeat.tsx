import { useState } from "react";
import { saveAnswer } from "../../api/client";
import type { CheckpointBeat as CheckpointBeatType, ViewpointOption } from "../../api/types";

interface Props {
  beat: CheckpointBeatType;
  storyId: string;
  studentId: string;
  options: ViewpointOption[];
  onSubmit: () => void;
}

export function CheckpointBeat({ beat, storyId, studentId, options, onSubmit }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [reflection, setReflection] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(true);
    saveAnswer(storyId, {
      student_id: studentId,
      reflection,
      selected_option: selected ?? undefined,
    }).catch(() => {});
    onSubmit();
  }

  if (submitted) {
    return (
      <section className="beat beat-checkpoint">
        <h2>Your turn</h2>
        {selected && <span className="selected-badge">You sided with {selected}</span>}
        <p className="reflection-saved">Your reflection is saved. Read on to see what actually happened.</p>
      </section>
    );
  }

  return (
    <section className="beat beat-checkpoint">
      <h2>Your turn</h2>
      <p className="checkpoint-question">{beat.question}</p>

      {options.length > 0 && (
        <div className="mcq-options">
          {options.map((opt) => (
            <button
              key={opt.author}
              type="button"
              className={`option-btn${selected === opt.author ? " selected" : ""}`}
              onClick={() => setSelected(opt.author)}
            >
              <span className="option-author">{opt.author}</span>
              {opt.title.replace(/^Position [A-Z] — /, "")}
            </button>
          ))}
        </div>
      )}

      {(selected || options.length === 0) && (
        <form onSubmit={handleSubmit}>
          <label className="reflection-label">
            Briefly explain the trade-off behind your choice
          </label>
          <textarea
            value={reflection}
            onChange={(e) => setReflection(e.target.value)}
            placeholder="Write down your own judgment before reading on..."
            rows={5}
            required
          />
          <button type="submit">Submit and reveal the decision</button>
        </form>
      )}
    </section>
  );
}
