import { useState } from "react";
import { Link } from "react-router-dom";
import { useStudent } from "../context/StudentContext";

// Shared warm header (logo + name avatar with an edit popover). Reuses the
// landing page's global CSS classes so it stays pixel-identical across pages.
export function AppHeader() {
  const { studentId, setStudentId } = useStudent();
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [nameDraft, setNameDraft] = useState(studentId);

  function openPopover() {
    setNameDraft(studentId);
    setPopoverOpen(true);
  }

  function saveName() {
    const name = nameDraft.trim();
    if (!name) return;
    setStudentId(name);
    setPopoverOpen(false);
  }

  const initial = studentId.trim() ? studentId.trim()[0].toUpperCase() : "?";

  return (
    <header className="landing-header">
      <Link className="landing-logo" to="/">
        <span><span className="git">Git</span>Stories</span>
      </Link>

      <div className="name-menu">
        <button
          type="button"
          className={studentId ? "name-avatar" : "name-avatar unset"}
          onClick={openPopover}
          aria-haspopup="dialog"
          aria-expanded={popoverOpen}
        >
          <span className="av" aria-hidden="true">{initial}</span>
          {studentId ? `Hi, ${studentId} 👋` : "Set your name"}
          <span className="chev" aria-hidden="true">▾</span>
        </button>

        {popoverOpen && (
          <>
            <div className="popover-backdrop" onClick={() => setPopoverOpen(false)} />
            <div className="name-popover" role="dialog" aria-label="Set your name">
              <label htmlFor="header-name-input">Your name or student ID</label>
              <input
                id="header-name-input"
                autoFocus
                value={nameDraft}
                onChange={(e) => setNameDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") saveName();
                  if (e.key === "Escape") setPopoverOpen(false);
                }}
                placeholder="e.g. Alice or s1234567"
              />
              <p className="pop-hint">We save your progress and quiz answers under this name.</p>
              <div className="pop-actions">
                <button className="btn-sm mint" onClick={saveName} disabled={!nameDraft.trim()}>
                  Save
                </button>
                <button className="btn-sm ghost" onClick={() => setPopoverOpen(false)}>
                  Cancel
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </header>
  );
}
