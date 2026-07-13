import re
import time
from datetime import datetime, timedelta

import requests


class GitHubClient:
    def __init__(self, token: str):
        self.token = token

    def _headers(self):
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def _request(self, url: str, params=None, max_retries=3):
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self._headers(), params=params)
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
        print(f"  Failed after {max_retries} attempts. Skipping.")
        return {}

    def get(self, repo: str, endpoint: str, params=None, max_retries=3):
        url = f"https://api.github.com/repos/{repo}/{endpoint}"
        return self._request(url, params=params, max_retries=max_retries)

    def search_repositories(
        self,
        query: str,
        min_stars: int = 500,
        per_page: int = 10,
        extra_qualifiers: list[str] | None = None,
    ):
        active_since = (datetime.utcnow() - timedelta(days=180)).strftime("%Y-%m-%d")
        qualifiers = list(extra_qualifiers or [])
        # The default popularity floor only applies when the caller didn't
        # pick a stars range themselves (e.g. the "< 100 stars" bucket).
        if not any(q.startswith("stars:") for q in qualifiers):
            qualifiers.append(f"stars:>={min_stars}")
        qualifiers.append(f"pushed:>={active_since}")
        full_query = " ".join([query, *qualifiers])
        result = self._request(
            "https://api.github.com/search/repositories",
            params={"q": full_query, "sort": "stars", "order": "desc", "per_page": per_page},
        )
        return result.get("items", [])

    def get_contributor_count(self, repo: str) -> int | None:
        """Cheap contributor count: request one contributor per page and read
        the total from the Link header's last-page number. Returns None when
        GitHub can't answer (network error, or 403 "list too large") so
        callers can fail open instead of dropping the repo."""
        url = f"https://api.github.com/repos/{repo}/contributors"
        try:
            response = requests.get(
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
