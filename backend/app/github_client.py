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

    def search_repositories(self, query: str, min_stars: int = 500, per_page: int = 10):
        active_since = (datetime.utcnow() - timedelta(days=180)).strftime("%Y-%m-%d")
        full_query = f"{query} stars:>={min_stars} pushed:>={active_since}"
        result = self._request(
            "https://api.github.com/search/repositories",
            params={"q": full_query, "sort": "stars", "order": "desc", "per_page": per_page},
        )
        return result.get("items", [])
