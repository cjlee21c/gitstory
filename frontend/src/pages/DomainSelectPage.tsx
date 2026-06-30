import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useStudent } from "../context/StudentContext";

export function DomainSelectPage() {
  const { studentId, setStudentId } = useStudent();
  const [nameInput, setNameInput] = useState(studentId);
  const [interest, setInterest] = useState("");
  const navigate = useNavigate();

  function saveAndGo(path: string) {
    const name = nameInput.trim();
    if (!name) return;
    setStudentId(name);
    navigate(path);
  }

  function handleDiscover(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = interest.trim();
    if (!trimmed || !nameInput.trim()) return;
    setStudentId(nameInput.trim());
    navigate(`/discover?interest=${encodeURIComponent(trimmed)}`);
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

      <h2>Discover by Interest</h2>
      <p>What kind of software engineering are you interested in?</p>
      <form onSubmit={handleDiscover}>
        <input
          value={interest}
          onChange={(e) => setInterest(e.target.value)}
          placeholder="e.g. game engines, distributed databases, compilers..."
        />
        <button type="submit" disabled={!nameInput.trim() || !interest.trim()}>
          Find repos
        </button>
      </form>
    </div>
  );
}
