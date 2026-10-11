// GitHub URLs for the repos and discussions a story is mined from.
//
// A story_id is "<owner>/<repo>#<number>", and that number is always a merged
// pull request — pass1 searches `is:pr is:merged`, so there is no separate
// issue page. /pull/<number> is the exact conversation the workspace was
// written from.

export function repoUrl(repo: string): string {
  return `https://github.com/${repo}`;
}

/** Null when the id carries no PR number, so callers render nothing rather
 *  than a link to a repo-root URL with a stray slash. */
export function storyUrl(storyId: string): string | null {
  const hash = storyId.lastIndexOf("#");
  if (hash <= 0) return null;
  const repo = storyId.slice(0, hash);
  const number = storyId.slice(hash + 1);
  if (!/^\d+$/.test(number)) return null;
  return `https://github.com/${repo}/pull/${number}`;
}
