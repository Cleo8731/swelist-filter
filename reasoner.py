### reasoner.py -- a tiny, platform-agnostic model client.
###
### Everything platform-specific lives in PLATFORMS / FAMILY_BY_PREFIX. Switching
### model or platform is an .env change (DIGEST_PLATFORM / DIGEST_MODEL); no code
### changes. Three API families are supported: openai_chat (chat completions, the
### common case), anthropic_messages, and openai_responses.
###
### NB: several models on OpenCode Go are REASONING models -- they spend part of
### the completion budget on hidden reasoning tokens before writing the answer.
### So max_tokens must be generous, and a finish_reason of "length" means the
### visible answer was cut off, not that the model chose to stop.

import gzip
import json
import os
import time
import zlib
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_TIMEOUT = 600
DEFAULT_MAX_TOKENS = 40000
MAX_TOKENS_CEILING = 200000
UA = "SimplifyDigest/1.0 (+local scheduled job)"

# platform -> base URL + the env var holding its key (None = no auth).
PLATFORMS = {
    "opencode-go": {"base_url": "https://opencode.ai/zen/go/v1",
                    "auth": "OPENCODE_GO_KEY"},
    "opencode":    {"base_url": "https://opencode.ai/zen/v1",
                    "auth": "OPENCODE_API_KEY"},
    "openrouter":  {"base_url": "https://openrouter.ai/api/v1",
                    "auth": "OPENROUTER_API_KEY"},
    "ollama":      {"base_url": "http://100.110.87.49:11434/v1",
                    "auth": None},
}

# Model-id prefix -> API family. OpenCode Go/Console serve different families for
# different models; everything else (DeepSeek, GLM, Kimi, MiMo, LongCat, ...) is
# OpenAI chat-completions compatible.
FAMILY_BY_PREFIX = (
    ("grok", "openai_responses"),
    ("gpt", "openai_responses"),
    ("muse", "openai_responses"),
    ("minimax", "anthropic_messages"),
    ("qwen", "anthropic_messages"),
)


def family_for(model):
    for prefix, fam in FAMILY_BY_PREFIX:
        if model.startswith(prefix):
            return fam
    return "openai_chat"


def _read(resp):
    raw = resp.read()
    enc = (resp.headers.get("Content-Encoding") or "").lower()
    if enc == "gzip":
        raw = gzip.decompress(raw)
    elif enc == "deflate":
        raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw.decode("utf-8", "replace")


def _build(family, model, system, user, max_tokens, temperature):
    if family == "anthropic_messages":
        return "/messages", {
            "model": model, "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": max_tokens, "temperature": temperature,
        }
    if family == "openai_responses":
        return "/responses", {
            "model": model, "instructions": system,
            "input": [{"role": "user", "content": user}],
            "max_output_tokens": max_tokens, "temperature": temperature,
        }
    return "/chat/completions", {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": max_tokens, "temperature": temperature,
    }


def _extract(family, data):
    """Return (text, truncated). Reasoning tokens are intentionally discarded."""
    if family == "anthropic_messages":
        text = "".join(b.get("text", "") for b in data.get("content", []))
        return text, data.get("stop_reason") == "max_tokens"
    if family == "openai_responses":
        text = data.get("output_text") or "".join(
            c.get("text", "") for item in data.get("output", [])
            for c in item.get("content", [])
            if c.get("type") in ("output_text", "text"))
        return text, data.get("status") == "incomplete"
    choice = (data.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    return text, choice.get("finish_reason") == "length"


def complete(system, user, platform, model, max_tokens=DEFAULT_MAX_TOKENS,
             temperature=0.3, timeout=DEFAULT_TIMEOUT, retries=4, session=None):
    """Send one system+user prompt, return the model's text.

    On a truncated answer (finish_reason == 'length') the token budget is doubled
    and the call retried, up to MAX_TOKENS_CEILING.
    """
    conf = PLATFORMS.get(platform)
    if conf is None:
        raise ValueError("unknown DIGEST_PLATFORM %r (choices: %s)"
                         % (platform, ", ".join(PLATFORMS)))
    key = os.environ.get(conf["auth"]) if conf["auth"] else None
    if conf["auth"] and not key:
        raise RuntimeError("%s is not set (required for platform %r)"
                           % (conf["auth"], platform))

    family = family_for(model)
    headers = {"Content-Type": "application/json",
               "Accept-Encoding": "gzip, deflate",
               "User-Agent": UA}
    if session:
        headers["x-opencode-session"] = session
    if key:
        headers["Authorization"] = "Bearer %s" % key

    budget = max_tokens
    last = None
    for attempt in range(retries):
        path, payload = _build(family, model, system, user, budget, temperature)
        url = conf["base_url"].rstrip("/") + path
        try:
            req = Request(url, data=json.dumps(payload).encode("utf-8"),
                          headers=headers, method="POST")
            with urlopen(req, timeout=timeout) as resp:
                data = json.loads(_read(resp))
            text, truncated = _extract(family, data)
            if truncated:
                last = ("answer truncated at max_tokens=%d (model spent its "
                        "budget on reasoning)" % budget)
                budget = min(budget * 2, MAX_TOKENS_CEILING)
                continue
            if not text:
                last = "empty response: %s" % json.dumps(data)[:300]
                time.sleep((2 ** attempt) * 5)
                continue
            return text
        except HTTPError as exc:
            last = "HTTP %s: %s" % (exc.code, _read(exc)[:400])
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep((2 ** attempt) * 5)
                continue
            raise RuntimeError(last)
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            last = str(exc)
            if attempt < retries - 1:
                time.sleep((2 ** attempt) * 5)
                continue
            raise RuntimeError(last)
    raise RuntimeError(last)
