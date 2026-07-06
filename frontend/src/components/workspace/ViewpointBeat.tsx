import type { ViewpointBeat as ViewpointBeatType } from "../../api/types";

export function ViewpointBeat({ beat }: { beat: ViewpointBeatType }) {
  return (
    <section className="beat beat-viewpoint">
      <img
        className="avatar"
        src={`https://github.com/${beat.author}.png?size=40`}
        alt={beat.author}
        onError={(e) => {
          (e.target as HTMLImageElement).style.display = "none";
        }}
      />
      <div className="bubble-content">
        <div className="bubble-header">
          <span className="bubble-author">{beat.author}</span>
          <span className="role-badge">{beat.author_role}</span>
        </div>
        <p className="bubble-body">{beat.body}</p>
      </div>
    </section>
  );
}
