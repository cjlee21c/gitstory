import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# Teacher-only token for the roster-wide answers export (GET
# /stories/{id}/answers). Read with .get() so a missing value can't stop the
# server booting — the gate in api/routes_answers.py fails closed when it is
# empty, so forgetting it on a deploy shuts that endpoint rather than silently
# reopening the whole class's reflections to the internet.
TEACHER_TOKEN = os.environ.get("TEACHER_TOKEN", "")
