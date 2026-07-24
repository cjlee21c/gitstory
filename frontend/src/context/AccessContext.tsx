import { useEffect, useState } from "react";
import { UNAUTHORIZED_EVENT, getAccessCode, setAccessCode } from "../api/access";
import { checkAccessCode } from "../api/client";

// Gates the whole app behind the shared class access code. Until a valid code
// is entered, children never render — so no token-spending screen is reachable.
// A stored code is re-verified on mount, and any later 401 (e.g. the code was
// rotated mid-deploy) drops back to the entry screen via UNAUTHORIZED_EVENT.
export function AccessProvider({ children }: { children: React.ReactNode }) {
  const [unlocked, setUnlocked] = useState(false);
  const [verifying, setVerifying] = useState(true); // checking a stored code on mount
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Re-verify any previously stored code when the app loads.
  useEffect(() => {
    const stored = getAccessCode();
    if (!stored) {
      setVerifying(false);
      return;
    }
    checkAccessCode(stored)
      .then((ok) => setUnlocked(ok))
      .catch(() => {})
      .finally(() => setVerifying(false));
  }, []);

  // A 401 from any request relocks the app.
  useEffect(() => {
    function relock() {
      setUnlocked(false);
    }
    window.addEventListener(UNAUTHORIZED_EVENT, relock);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, relock);
  }, []);

  async function submit() {
    const entered = code.trim();
    if (!entered) return;
    setSubmitting(true);
    setError("");
    const ok = await checkAccessCode(entered).catch(() => false);
    setSubmitting(false);
    if (ok) {
      setAccessCode(entered);
      setUnlocked(true);
    } else {
      setError("That access code isn't valid. Please check with your instructor.");
    }
  }

  if (unlocked) return <>{children}</>;

  return (
    <div className="landing">
      <div className="access-gate">
        <div className="landing-logo">
          <span><span className="git">Git</span>Stories</span>
        </div>
        <h1>Enter your access code</h1>
        <p>Your instructor shared a class access code. Enter it to continue.</p>
        <input
          className="filter-input"
          autoFocus
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="Access code"
          disabled={verifying || submitting}
        />
        {error && <p className="access-error">{error}</p>}
        <button
          className="btn-lg btn-mint"
          onClick={submit}
          disabled={verifying || submitting || !code.trim()}
        >
          {submitting ? "Checking…" : "Continue"}{" "}
          <span className="arrow" aria-hidden="true">→</span>
        </button>
      </div>
    </div>
  );
}
