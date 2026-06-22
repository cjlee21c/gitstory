import anthropic

from app.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SEMANTIC_GATE_MODEL = "claude-haiku-4-5-20251001"
WORKSPACE_GEN_MODEL = "claude-sonnet-4-6"
