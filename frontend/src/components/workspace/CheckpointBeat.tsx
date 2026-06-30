import { useState } from "react";
import { saveAnswer } from "../../api/client";
import type { CheckpointBeat as CheckpointBeatType } from "../../api/types";

interface Props {
  beat: CheckpointBeatType;
  storyId: string;
  studentId: string;
  onSubmit: () => void;
}

export function CheckpointBeat({ beat, storyId, studentId, onSubmit }: Props) {
  const [reflection, setReflection] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(true);
    saveAnswer(storyId, { student_id: studentId, reflection }).catch(() => {});
    onSubmit();
  }

  return (
    <section className="beat beat-checkpoint">
      <h2>Your turn</h2>
      <p>{beat.question}</p>
      {submitted ? (
        <p className="reflection-saved">Your reflection is saved below. Read on to see what actually happened.</p>
      ) : (
        <form onSubmit={handleSubmit}>
          <textarea
            value={reflection}
            onChange={(e) => setReflection(e.target.value)}
            placeholder="Write down your own judgment before reading on..."
            rows={5}
            required
          />
          <button type="submit">Submit reflection and reveal the decision</button>
        </form>
      )}
    </section>
  );
}
