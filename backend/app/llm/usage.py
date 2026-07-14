import json
import threading
import time
from pathlib import Path

# Per-1M-token prices (USD) for the models this app calls. Keep in sync with
# the model IDs in client.py.
_PRICING = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}

# Written outside .cache so it never collides with the library's cache globs.
LOG_PATH = Path(__file__).resolve().parent.parent.parent / "logs" / "token_usage.jsonl"
_lock = threading.Lock()


def _cost(model: str, input_tokens: int, output_tokens: int) -> float:
    in_price, out_price = _PRICING.get(model, (0.0, 0.0))
    return input_tokens * in_price / 1_000_000 + output_tokens * out_price / 1_000_000


def log_usage(label: str, model: str, input_tokens: int, output_tokens: int, **extra) -> None:
    """Appends one JSONL line per LLM call so token/cost usage survives past the
    server's stdout (which only lives in the running terminal). Safe to call from
    worker threads — every call site runs inside a ThreadPoolExecutor."""
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "label": label,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(_cost(model, input_tokens, output_tokens), 6),
        **extra,
    }
    line = json.dumps(entry, ensure_ascii=False)
    with _lock:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
