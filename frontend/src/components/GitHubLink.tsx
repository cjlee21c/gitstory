interface Props {
  href: string;
  label: string;
  /** Extra class for the few places that need their own sizing or spacing. */
  className?: string;
}

/** An outbound link to GitHub.
 *
 *  Several of these sit inside cards that are themselves clickable (RepoCard is
 *  a checkbox, LibCard a button). A click bubbles, so without stopPropagation
 *  opening the repo would also toggle the card's selection behind the new tab.
 *  That is owned here rather than at each call site, so a later caller can't
 *  forget it.
 */
export function GitHubLink({ href, label, className }: Props) {
  return (
    <a
      className={`gh-link${className ? ` ${className}` : ""}`}
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(e) => e.stopPropagation()}
      // The card around this is often keyboard-activatable too; Enter on the
      // link must follow the link, not re-trigger the card.
      onKeyDown={(e) => e.stopPropagation()}
    >
      <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
        <path d="M8 0a8 8 0 0 0-2.5 15.6c.4.1.5-.2.5-.4v-1.4c-2 .4-2.5-.5-2.7-1-.1-.3-.5-1-.9-1.2-.3-.2-.7-.6 0-.6.6 0 1 .6 1.2.8.7 1.2 1.9.9 2.3.7.1-.5.3-.9.5-1.1-1.8-.2-3.6-.9-3.6-4 0-.9.3-1.6.8-2.1-.1-.2-.4-1 .1-2.1 0 0 .7-.2 2.2.8a7.4 7.4 0 0 1 4 0c1.5-1 2.2-.8 2.2-.8.5 1.1.2 1.9.1 2.1.5.5.8 1.2.8 2.1 0 3.1-1.8 3.8-3.6 4 .3.3.6.8.6 1.6v2.3c0 .2.1.5.5.4A8 8 0 0 0 8 0Z" />
      </svg>
      <span>{label}</span>
      <span className="gh-link-out" aria-hidden="true">↗</span>
    </a>
  );
}
