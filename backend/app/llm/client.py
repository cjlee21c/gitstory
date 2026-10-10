import anthropic

from app.config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# No sampling parameters anywhere in this package: the Anthropic SDK dropped
# `temperature` from Messages.create() in 1.x, and the current model families
# reject it outright. Calls that passed temperature=0 for reproducibility now
# just take the default — stories are cached after their first generation, so
# a story is still only ever written once.
SEMANTIC_GATE_MODEL = "claude-haiku-4-5-20251001"
WORKSPACE_GEN_MODEL = "claude-sonnet-4-6"
