# GitStory — Search Filter Criteria (Draft for Review)

Two-stage search, as discussed: Stage 1 filters find candidate repositories (fast, no story mining);
Stage 2 filters decide which stories to mine from the 1–3 repositories the user selects.

## Stage 1 — Repository Filters (main screen)

| # | Criterion | Options | UI element |
|---|-----------|---------|------------|
| 1 | Domain | Gaming, Finance, Healthcare, Education, Developer Tools, Social/Communication, Media/Entertainment, Science/Research | Dropdown (single select) |
| 2 | Repository size | Small / Medium / Large | Checkbox (multi select) |
| 3 | Stars | < 100 / 100–1k / 1k–10k / > 10k | Dropdown or range slider |
| 4 | Contributors | < 10 / 10–50 / 50–200 / > 200 | Dropdown or range slider |
| 5 | Free keyword | e.g. "chess engine", "trading bot" — optional, refines within the domain | Search box |

**Open question — how to define Small/Medium/Large:** my proposal is by lines of code
(Small < 10k, Medium 10k–100k, Large > 100k), since stars and contributors are already
separate filters. Alternative: define size as a composite of stars + contributors + LOC.

Candidates to add later: primary programming language, activity (last commit within N months),
repository age, open-issue count, license.

## Stage 2 — Story Filters (after selecting 1–3 repositories)

| # | Criterion | Options | UI element |
|---|-----------|---------|------------|
| 1 | Quality requirement | Security, Performance, Usability, Maintainability | Checkbox chips (multi select) |

Starting with these four; the taxonomy extends naturally with the remaining ISO/IEC 25010
quality attributes as candidates: Reliability, Compatibility, Portability, Functional Suitability.

Candidates to add later:
- Discussion intensity — how debated the story was (comment count buckets)
- Outcome — resolved / rejected / still open
- Recency — stories from the last year vs. older

## How each filter is applied (one line each)

- Stage 1 filters map directly to GitHub search qualifiers (`stars:`, `size:`, topics/keywords) —
  no LLM cost, results in seconds.
- Stage 2 quality filters are applied during story screening: each candidate issue/PR is labeled
  with the quality attributes it touches, and only stories matching the user's selection go through
  deep analysis.
