import time

import requests


class GitHubClient:
    def __init__(self, token: str):
        self.token = token

    def get(self, repo: str, endpoint: str, params=None, max_retries=3):
        url = f"https://api.github.com/repos/{repo}/{endpoint}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, params=params)
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
