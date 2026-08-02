import re
import time
from datetime import datetime, timedelta

import requests
from requests.adapters import HTTPAdapter

# Discovery fans out to ~40 concurrent calls (searches, then one contributor
# count per candidate). Bare requests.get() builds a fresh session — and so a
# fresh TLS handshake — for every one of them, which dominated the wall time.
# One pooled session shared across threads reuses connections instead.
_POOL_SIZE = 50
_session = requests.Session()
_session.mount("https://", HTTPAdapter(pool_connections=_POOL_SIZE, pool_maxsize=_POOL_SIZE))


class GitHubClient:
    def __init__(self, token: str):
        self.token = token
        # Set when a request gave up on a rate limit instead of waiting it out.
        # Callers serving a user request use it to avoid caching a result that
        # is thin only because GitHub was throttling us.
        self.rate_limited = False

    def _headers(self):
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def _request(self, url: str, params=None, max_retries=3, wait_on_rate_limit=True):
        for attempt in range(max_retries):
            try:
                response = _session.get(url, headers=self._headers(), params=params)
                if response.status_code == 403:
                    # Mining runs offline and can afford to wait; anything on a
                    # request path would leave the user staring at a spinner for
                    # a full minute, so it gives up and returns what it has.
                    self.rate_limited = True
                    if not wait_on_rate_limit:
                        print("  Rate limit hit. Skipping (not waiting).")
                        return {}
                    print("  Rate limit hit. Sleeping 60s...")
                    time.sleep(60)
                    continue
                if response.status_code >= 500:
                    wait_time = 2**attempt
                    print(
                        f"  GitHub server error ({response.status_code}). "
                        f"Retrying in {wait_time}s... ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                wait_time = 2**attempt
                print(f"  Network exception: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        print(f"  Failed after {max_retries} attempts. Skipping.")
        return {}

    def get(self, repo: str, endpoint: str, params=None, max_retries=3):
        url = f"https://api.github.com/repos/{repo}/{endpoint}"
        return self._request(url, params=params, max_retries=max_retries)

    def get_repo(self, repo: str) -> dict:
        """Fetch a repo's root object (description, language, stars, topics).
        Fail-soft to {} — no LLM, one cheap REST call."""
        return self._request(f"https://api.github.com/repos/{repo}")

    def graphql(self, query: str, variables: dict, max_retries: int = 3) -> dict:
        """POST a GraphQL query. Same retry/back-off shape as _request. Returns
        the parsed JSON (with top-level "data"/"errors"), or {} after exhausting
        retries so callers can fail soft."""
        for attempt in range(max_retries):
            try:
                response = _session.post(
                    "https://api.github.com/graphql",
                    headers=self._headers(),
                    json={"query": query, "variables": variables},
                )
                if response.status_code == 403:
                    print("  Rate limit hit. Sleeping 60s...")
                    time.sleep(60)
                    continue
                if response.status_code >= 500:
                    wait_time = 2**attempt
                    print(
                        f"  GitHub server error ({response.status_code}). "
                        f"Retrying in {wait_time}s... ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                wait_time = 2**attempt
                print(f"  Network exception: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        print(f"  GraphQL failed after {max_retries} attempts.")
        return {}

    def search_repositories(
        self,
        query: str,
        min_stars: int = 500,
        per_page: int = 50,
        extra_qualifiers: list[str] | None = None,
        active_days: int | None = 180,
    ):
        """One page of repo search results, sorted by stars descending.

        `active_days=None` drops the recent-activity qualifier entirely. The
        180-day default is invisible to students, so discovery searches without
        it and re-applies the cutoff in Python — that way a thin result set can
        be relaxed without spending another round of search requests.
        """
        qualifiers = list(extra_qualifiers or [])
        # The default popularity floor only applies when the caller didn't
        # pick a stars range themselves (e.g. the "< 100 stars" bucket).
        if not any(q.startswith("stars:") for q in qualifiers):
            qualifiers.append(f"stars:>={min_stars}")
        if active_days is not None:
            active_since = (datetime.utcnow() - timedelta(days=active_days)).strftime("%Y-%m-%d")
            qualifiers.append(f"pushed:>={active_since}")
        full_query = " ".join([query, *qualifiers])
        result = self._request(
            "https://api.github.com/search/repositories",
            params={"q": full_query, "sort": "stars", "order": "desc", "per_page": per_page},
            wait_on_rate_limit=False,
        )
        return result.get("items", [])

    def get_contributor_count(self, repo: str) -> int | None:
        """Cheap contributor count: request one contributor per page and read
        the total from the Link header's last-page number. Returns None when
        GitHub can't answer (network error, or 403 "list too large") so
        callers can fail open instead of dropping the repo."""
        url = f"https://api.github.com/repos/{repo}/contributors"
        try:
            response = _session.get(
                url,
                headers=self._headers(),
                params={"per_page": 1, "anonymous": "true"},
            )
            if response.status_code != 200:
                return None
            link = response.headers.get("Link", "")
            match = re.search(r'[?&]page=(\d+)>; rel="last"', link)
            if match:
                return int(match.group(1))
            # No Link header means everything fit on one page (0 or 1).
            return len(response.json())
        except requests.exceptions.RequestException:
            return None
