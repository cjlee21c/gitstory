import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useStudent } from "../context/StudentContext";
import { CONTRIBUTORS, DOMAINS, SIZES, STARS } from "../filters";

export function DomainSelectPage() {
  const { studentId, setStudentId } = useStudent();
  const [nameInput, setNameInput] = useState(studentId);
  const [domain, setDomain] = useState("");
  const [sizes, setSizes] = useState<string[]>([]);
  const [stars, setStars] = useState("");
  const [contributors, setContributors] = useState("");
  const [keyword, setKeyword] = useState("");
  const navigate = useNavigate();

  function saveAndGo(path: string) {
    const name = nameInput.trim();
    if (!name) return;
    setStudentId(name);
    navigate(path);
  }

  function toggleSize(id: string) {
    setSizes((prev) => (prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]));
  }

  function handleDiscover(e: React.FormEvent) {
    e.preventDefault();
    if (!domain || !nameInput.trim()) return;
    setStudentId(nameInput.trim());
    const params = new URLSearchParams({ domain });
    if (sizes.length) params.set("sizes", sizes.join(","));
    if (stars) params.set("stars", stars);
    if (contributors) params.set("contributors", contributors);
    if (keyword.trim()) params.set("keyword", keyword.trim());
    navigate(`/discover?${params.toString()}`);
  }

  return (
    <div className="page page-narrow">
      <h1>GitStories</h1>

      <div className="field">
        <label htmlFor="student-id">Your name or student ID</label>
        <input
          id="student-id"
          value={nameInput}
          onChange={(e) => setNameInput(e.target.value)}
          placeholder="e.g. Alice or s1234567"
          autoFocus
        />
      </div>

      <hr />

      <h2>Browse Library</h2>
      <p>Explore pre-built stories — loads instantly, no waiting.</p>
      <button
        onClick={() => saveAndGo("/library")}
        disabled={!nameInput.trim()}
      >
        Browse Library
      </button>

      <hr />

      <h2>Find Repositories</h2>
      <p>Pick a domain and narrow the search with the filters below.</p>
      <form className="filter-form" onSubmit={handleDiscover}>
        <div className="field">
          <label htmlFor="domain">Domain</label>
          <select id="domain" value={domain} onChange={(e) => setDomain(e.target.value)}>
            <option value="">Select a domain...</option>
            {DOMAINS.map((d) => (
              <option key={d.id} value={d.id}>
                {d.label}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Repository size</label>
          <div className="filter-row">
            {SIZES.map((s) => (
              <label key={s.id} className="checkbox-option">
                <input
                  type="checkbox"
                  checked={sizes.includes(s.id)}
                  onChange={() => toggleSize(s.id)}
                />
                {s.label}
              </label>
            ))}
          </div>
        </div>

        <div className="filter-row">
          <div className="field">
            <label htmlFor="stars">Stars</label>
            <select id="stars" value={stars} onChange={(e) => setStars(e.target.value)}>
              <option value="">Any</option>
              {STARS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="contributors">Contributors</label>
            <select
              id="contributors"
              value={contributors}
              onChange={(e) => setContributors(e.target.value)}
            >
              <option value="">Any</option>
              {CONTRIBUTORS.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="field">
          <label htmlFor="keyword">Keyword (optional)</label>
          <input
            id="keyword"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder='e.g. "chess engine", "trading bot"...'
          />
        </div>

        <button type="submit" disabled={!nameInput.trim() || !domain}>
          Find repos
        </button>
      </form>
    </div>
  );
}
