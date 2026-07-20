import type { ReactNode } from "react";

// Conservative code-token detector — deliberately narrow so ordinary prose is
// left alone. Matches: `backticked`, snake_case, dotted.identifiers (first
// segment 2+ chars, to skip "e.g."/"i.e."), and func() calls.
const CODE_RE =
  /(`[^`]+`|\b[A-Za-z_][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b|\b[a-z][A-Za-z0-9]+(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b|\b[A-Za-z_][A-Za-z0-9_]*\(\))/g;

export function highlightCode(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let last = 0;
  let key = 0;
  let m: RegExpExecArray | null;
  CODE_RE.lastIndex = 0;
  while ((m = CODE_RE.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index));
    const raw = m[0];
    const token = raw.startsWith("`") && raw.endsWith("`") ? raw.slice(1, -1) : raw;
    nodes.push(
      <code key={key++} className="inline-code">
        {token}
      </code>,
    );
    last = m.index + raw.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}
