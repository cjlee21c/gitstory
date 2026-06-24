import type { Beat } from "../../api/types";
import { CheckpointBeat } from "./CheckpointBeat";
import { ContextBeat } from "./ContextBeat";
import { DecisionBeat } from "./DecisionBeat";
import { DilemmaBeat } from "./DilemmaBeat";
import { LessonsBeat } from "./LessonsBeat";
import { ViewpointBeat } from "./ViewpointBeat";

interface Props {
  beat: Beat;
  onCheckpointSubmit: () => void;
}

export function BeatRenderer({ beat, onCheckpointSubmit }: Props) {
  switch (beat.type) {
    case "context":
      return <ContextBeat beat={beat} />;
    case "dilemma":
      return <DilemmaBeat beat={beat} />;
    case "viewpoint":
      return <ViewpointBeat beat={beat} />;
    case "checkpoint":
      return <CheckpointBeat beat={beat} onSubmit={onCheckpointSubmit} />;
    case "decision":
      return <DecisionBeat beat={beat} />;
    case "lessons":
      return <LessonsBeat beat={beat} />;
  }
}
