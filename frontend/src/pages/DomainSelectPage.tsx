import { useState } from "react";
import { useNavigate } from "react-router-dom";

export function DomainSelectPage() {
  const [interest, setInterest] = useState("");
  const navigate = useNavigate();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = interest.trim();
    if (!trimmed) return;
    navigate(`/discover?interest=${encodeURIComponent(trimmed)}`);
  }

  return (
    <div className="page page-narrow">
      <h1>GitStories</h1>
      <p>What kind of software engineering are you interested in?</p>
      <form onSubmit={handleSubmit}>
        <input
          value={interest}
          onChange={(e) => setInterest(e.target.value)}
          placeholder="e.g. game engines, distributed databases, compilers..."
          autoFocus
        />
        <button type="submit">Find repos</button>
      </form>
    </div>
  );
}
