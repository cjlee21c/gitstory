import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getLibrary } from "../api/client";
import type { LibraryEntry } from "../api/types";
import { AppHeader } from "../components/AppHeader";
import { DOMAIN_ICONS, DOMAINS } from "../filters";

// Fixed semantic tones for the 4 controlled qualities (shared with the catalog).
const QUALITY_TONE: Record<string, string> = {
  security: "tag-security",
  performance: "tag-performance",
  usability: "tag-usability",
  maintainability: "tag-maintainability",
};

const OTHER = "_other";

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="landing">
      <div className="landing-inner">
        <AppHeader />
        {children}
      </div>
    </div>
  );
}

function LibCard({ entry, onOpen }: { entry: LibraryEntry; onOpen: () => void }) {
  const uniqueQualities = [...new Set(entry.stories.flatMap((s) => s.qualities))];
  const previews = entry.stories.slice(0, 3);
  const extra = entry.stories.length - previews.length;
  return (
    <div
      className="lib-card"
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === " " || e.key === "Enter") {
          e.preventDefault();
          onOpen();
        }
      }}
    >
      <div className="lib-card-head">
        <svg className="repo-ghico" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path d="M8 0a8 8 0 0 0-2.5 15.6c.4.1.5-.2.5-.4v-1.4c-2 .4-2.5-.5-2.7-1-.1-.3-.5-1-.9-1.2-.3-.2-.7-.6 0-.6.6 0 1 .6 1.2.8.7 1.2 1.9.9 2.3.7.1-.5.3-.9.5-1.1-1.8-.2-3.6-.9-3.6-4 0-.9.3-1.6.8-2.1-.1-.2-.4-1 .1-2.1 0 0 .7-.2 2.2.8a7.4 7.4 0 0 1 4 0c1.5-1 2.2-.8 2.2-.8.5 1.1.2 1.9.1 2.1.5.5.8 1.2.8 2.1 0 3.1-1.8 3.8-3.6 4 .3.3.6.8.6 1.6v2.3c0 .2.1.5.5.4A8 8 0 0 0 8 0Z"/>
        </svg>
        <h2 className="repo-name">{entry.repo}</h2>
        <span className="lib-count">
          {entry.stories.length} stor{entry.stories.length === 1 ? "y" : "ies"}
        </span>
      </div>

      {entry.description && <p className="lib-desc">{entry.description}</p>}

      {uniqueQualities.length > 0 && (
        <div className="story-tags">
          {uniqueQualities.map((q) => (
            <span key={q} className={`tag ${QUALITY_TONE[q] ?? "tag-neutral"}`}>
              {q}
            </span>
          ))}
        </div>
      )}

      <ul className="lib-preview">
        {previews.map((s) => (
          <li key={s.story_id}>{s.title}</li>
        ))}
        {extra > 0 && <li className="lib-more">+{extra} more</li>}
      </ul>

      <div className="story-card-foot">
        <span className="story-cta">
          Explore stories <span className="arrow" aria-hidden="true">→</span>
        </span>
      </div>
    </div>
  );
}

export function LibraryPage() {
  const [entries, setEntries] = useState<LibraryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getLibrary()
      .then(setEntries)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  function openRepo(repo: string) {
    navigate(`/stories?repo=${encodeURIComponent(repo)}`);
  }

  if (loading) {
    return (
      <Shell>
        <main className="catalog-main">
          <section className="catalog-hero">
            <h1>Your Story Library 📚</h1>
            <p>Loading ready-made engineering stories…</p>
          </section>
          <div className="repo-grid" aria-busy="true">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="lib-card skeleton" aria-hidden="true">
                <div className="sk-line sk-title" />
                <div className="sk-line sk-tag" />
                <div className="sk-line sk-short" />
              </div>
            ))}
          </div>
        </main>
      </Shell>
    );
  }

  if (error) {
    return (
      <Shell>
        <main className="catalog-main">
          <div className="warn-card">{error}</div>
        </main>
      </Shell>
    );
  }

  if (entries.length === 0) {
    return (
      <Shell>
        <main className="landing-main">
          <div className="discover-empty">
            <h1>Your library is empty 📚</h1>
            <p>Search GitHub to mine your first engineering stories — they'll show up here.</p>
            <button className="btn-lg btn-mint" onClick={() => navigate("/")}>
              Find repositories <span className="arrow" aria-hidden="true">→</span>
            </button>
          </div>
        </main>
      </Shell>
    );
  }

  const totalStories = entries.reduce((n, e) => n + e.stories.length, 0);

  // Group repos by domain, keeping the DOMAINS order and pooling anything
  // unclassified into a trailing "Other" section.
  const groups = new Map<string, LibraryEntry[]>();
  for (const e of entries) {
    const key = e.domain && DOMAINS.some((d) => d.id === e.domain) ? e.domain : OTHER;
    const list = groups.get(key) ?? [];
    list.push(e);
    groups.set(key, list);
  }
  const sectionIds = [...DOMAINS.map((d) => d.id), OTHER].filter((id) => groups.has(id));

  return (
    <Shell>
      <main className="catalog-main">
        <button className="back-link" onClick={() => navigate("/")}>
          ← Back to start
        </button>

        <section className="catalog-hero">
          <span className="step-capsule">📚 Ready to read</span>
          <h1>Your Story Library</h1>
          <p>
            {entries.length} repositor{entries.length === 1 ? "y" : "ies"} · {totalStories}{" "}
            engineering stor{totalStories === 1 ? "y" : "ies"}, grouped by domain. Pick one to dive in.
          </p>
        </section>

        {sectionIds.map((id) => {
          const list = groups.get(id)!;
          const label = id === OTHER ? "Other" : DOMAINS.find((d) => d.id === id)!.label;
          const icon = id === OTHER ? "📦" : DOMAIN_ICONS[id];
          return (
            <section key={id} className="lib-section">
              <h2 className="lib-section-title">
                <span aria-hidden="true">{icon}</span> {label}
                <span className="lib-section-count">{list.length}</span>
              </h2>
              <div className="repo-grid">
                {list.map((entry) => (
                  <LibCard key={entry.repo} entry={entry} onOpen={() => openRepo(entry.repo)} />
                ))}
              </div>
            </section>
          );
        })}
      </main>
    </Shell>
  );
}
