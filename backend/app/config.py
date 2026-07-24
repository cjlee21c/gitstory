import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# Shared class access code. Every request (except /health) must carry it in the
# X-Access-Code header; the gate in app/api/deps.py compares against this value.
# Its only job is to stop our GitHub/Anthropic tokens from being spent by
# strangers — rotate it by changing this env var and redeploying.
ACCESS_CODE = os.environ["ACCESS_CODE"]
