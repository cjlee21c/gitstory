import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useStudent } from "../context/StudentContext";
import { CONTRIBUTORS, DOMAINS, SIZES, STARS } from "../filters";

// Emoji per domain id. Kept here (not in filters.ts) so the backend-mirrored
// id list stays clean.
const DOMAIN_ICONS: Record<string, string> = {
  gaming: "🎮",
  finance: "💰",
  healthcare: "🩺",
  education: "🎓",
  developer_tools: "🛠️",
  social: "💬",
  media: "🎬",
  science: "🔬",
};

export function DomainSelectPage() {
  const { studentId, setStudentId } = useStudent();
  const navigate = useNavigate();

  // Filter state (unchanged semantics from the original page)
  const [domain, setDomain] = useState("");
  const [sizes, setSizes] = useState<string[]>([]);
  const [stars, setStars] = useState("");
  const [contributors, setContributors] = useState("");
  const [keyword, setKeyword] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);

  // Name popover (header avatar). pendingAction runs after a first-time name
  // is saved, so clicking a card while unnamed prompts, then continues.
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [nameDraft, setNameDraft] = useState(studentId);
  const pendingAction = useRef<(() => void) | null>(null);

  function toggleSize(id: string) {
    setSizes((prev) => (prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]));
  }

  function openNamePopover(pending?: () => void) {
    setNameDraft(studentId);
    pendingAction.current = pending ?? null;
    setPopoverOpen(true);
  }

  function closePopover() {
    setPopoverOpen(false);
    pendingAction.current = null;
  }

  function saveName() {
    const name = nameDraft.trim();
    if (!name) return;
    setStudentId(name);
    setPopoverOpen(false);
    const act = pendingAction.current;
    pendingAction.current = null;
    act?.();
  }

  // Runs `action` if a name exists; otherwise prompts for one first.
  function requireName(action: () => void) {
    if (studentId.trim()) action();
    else openNamePopover(action);
  }

  function doDiscover() {
    if (!domain) return;
    const params = new URLSearchParams({ domain });
    if (sizes.length) params.set("sizes", sizes.join(","));
    if (stars) params.set("stars", stars);
    if (contributors) params.set("contributors", contributors);
    if (keyword.trim()) params.set("keyword", keyword.trim());
    navigate(`/discover?${params.toString()}`);
  }

  const initial = studentId.trim() ? studentId.trim()[0].toUpperCase() : "?";

  return (
    <div className="landing">
      <div className="landing-inner">
        <header className="landing-header">
          <div className="landing-logo">
            <span className="logo-mark" aria-hidden="true">📖</span>
            <span><span className="git">Git</span>Stories</span>
          </div>

          <div className="name-menu">
            <button
              type="button"
              className={studentId ? "name-avatar" : "name-avatar unset"}
              onClick={() => openNamePopover()}
              aria-haspopup="dialog"
              aria-expanded={popoverOpen}
            >
              <span className="av" aria-hidden="true">{initial}</span>
              {studentId ? `Hi, ${studentId} 👋` : "Set your name"}
              <span className="chev" aria-hidden="true">▾</span>
            </button>

            {popoverOpen && (
              <>
                <div className="popover-backdrop" onClick={closePopover} />
                <div className="name-popover" role="dialog" aria-label="Set your name">
                  <label htmlFor="name-input">Your name or student ID</label>
                  <input
                    id="name-input"
                    autoFocus
                    value={nameDraft}
                    onChange={(e) => setNameDraft(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && saveName()}
                    placeholder="e.g. Alice or s1234567"
                  />
                  <p className="pop-hint">We save your progress and quiz answers under this name.</p>
                  <div className="pop-actions">
                    <button className="btn-sm mint" onClick={saveName} disabled={!nameDraft.trim()}>
                      Save
                    </button>
                    <button className="btn-sm ghost" onClick={closePopover}>
                      Cancel
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </header>

        <main className="landing-main">
        <section className="landing-hero">
          <h1>How would you like to learn today?</h1>
          <p>Step into real open-source debates and decide what you'd do.</p>
        </section>

        <div className="landing-cards">
          <div className="landing-card primary">
            <div className="card-icon" aria-hidden="true">📚</div>
            <div className="card-head">
              <h2>Browse Library</h2>
              <span className="badge-instant">Instant</span>
            </div>
            <p className="card-desc">
              Explore hand-picked engineering stories. Loads instantly — no waiting.
            </p>
            <button
              className="btn-lg btn-mint"
              onClick={() => requireName(() => navigate("/library"))}
            >
              Start Browsing <span className="arrow" aria-hidden="true">→</span>
            </button>
          </div>

          <div className="landing-card secondary">
            <div className="card-icon" aria-hidden="true">🔍</div>
            <div className="card-head">
              <h2>Find Repositories</h2>
            </div>
            <p className="card-desc">
              Search and analyze any open-source project on GitHub by domain and popularity.
            </p>
            <button
              className="btn-lg btn-yellow"
              onClick={() => setFiltersOpen((o) => !o)}
              aria-expanded={filtersOpen}
            >
              {filtersOpen ? "Hide Filters" : "Open Filters"}{" "}
              <span className="arrow" aria-hidden="true">→</span>
            </button>
          </div>
        </div>

        {filtersOpen && (
          <div className="filter-panel">
            <div className="filter-group">
              <span className="fg-label">Domain</span>
              <div className="pill-group">
                {DOMAINS.map((d) => (
                  <button
                    key={d.id}
                    type="button"
                    className="pill"
                    aria-pressed={domain === d.id}
                    onClick={() => setDomain((prev) => (prev === d.id ? "" : d.id))}
                  >
                    <span className="emoji" aria-hidden="true">{DOMAIN_ICONS[d.id]}</span>
                    {d.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="filter-group">
              <span className="fg-label">Repository size</span>
              <div className="seg">
                {SIZES.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    className="seg-item"
                    aria-pressed={sizes.includes(s.id)}
                    onClick={() => toggleSize(s.id)}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="filter-cols">
              <div className="filter-group">
                <span className="fg-label">Stars</span>
                <div className="pill-group">
                  <button
                    type="button"
                    className="pill"
                    aria-pressed={stars === ""}
                    onClick={() => setStars("")}
                  >
                    Any
                  </button>
                  {STARS.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      className="pill"
                      aria-pressed={stars === s.id}
                      onClick={() => setStars((prev) => (prev === s.id ? "" : s.id))}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="filter-group">
                <span className="fg-label">Contributors</span>
                <div className="pill-group">
                  <button
                    type="button"
                    className="pill"
                    aria-pressed={contributors === ""}
                    onClick={() => setContributors("")}
                  >
                    Any
                  </button>
                  {CONTRIBUTORS.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      className="pill"
                      aria-pressed={contributors === c.id}
                      onClick={() => setContributors((prev) => (prev === c.id ? "" : c.id))}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="filter-group">
              <span className="fg-label">
                Keyword{" "}
                <span style={{ fontWeight: 400, color: "var(--warm-muted)" }}>(optional)</span>
              </span>
              <input
                className="filter-input"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder='e.g. "chess engine", "trading bot"…'
              />
            </div>

            <div className="filter-actions">
              <button
                className="btn-lg btn-mint"
                onClick={() => requireName(doDiscover)}
                disabled={!domain}
              >
                Find repos <span className="arrow" aria-hidden="true">→</span>
              </button>
            </div>
          </div>
        )}
        </main>
      </div>
    </div>
  );
}
