### digest.py -- the LLM evaluation stage.
###
### Composes the system message from the task + criteria (`prompt/`) and the
### candidate profile (`profile/`), sends it with today's scraped.json
### (+ broken.json), validates the result, and writes output/<date>/digest.html.
### It does NOT send anything; sender.py does.
###
### The digest is labelled with the DATA's date (the output folder name), not the
### wall-clock date, so a re-run or a run that crosses midnight stays consistent.

import json
import re
import sys
from datetime import date

from config import (OUTPUT_DIR, BASE_DIR, DIGEST_PLATFORM, DIGEST_MODEL,
                    DIGEST_MAX_TOKENS)
from utils import json_load
import reasoner

# System message order: mechanics, then rules, then the candidate. Fixed order so
# prompt caching stays warm across runs.
DOCS = (
    ("prompt", "task.md"),
    ("prompt", "criteria.md"),
    ("profile", "resume.txt"),
    ("profile", "self_assessment.md"),
    ("profile", "preferences.md"),
)

FENCE_RE = re.compile(r"^\s*```[a-zA-Z]*\s*|\s*```\s*$")
SUBJECT_RE = re.compile(r"<!--\s*SUBJECT:.*?-->", re.S)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def data_date():
    """The date the data belongs to (the output folder), not wall-clock today."""
    name = OUTPUT_DIR.name
    return name if DATE_RE.match(name) else date.today().isoformat()


def build_system():
    """Concatenate the documents into one system message, flagging any missing."""
    parts = []
    for folder, name in DOCS:
        path = BASE_DIR / folder / name
        if path.exists():
            body = path.read_text(encoding="utf-8").strip() or "(empty file)"
        else:
            body = "(MISSING - %s/%s not found)" % (folder, name)
        parts.append("<!-- ===== %s/%s ===== -->\n%s" % (folder, name, body))
    return "\n\n".join(parts)


def read_inputs():
    scraped_path = OUTPUT_DIR / "scraped.json"
    if not scraped_path.exists():
        return None, None
    scraped = json_load(scraped_path)
    broken_path = OUTPUT_DIR / "broken.json"
    broken = json_load(broken_path) if broken_path.exists() else []
    return scraped, broken


def build_user_message(scraped, broken):
    return ("Today's date: %s\n\n=== scraped.json ===\n%s\n\n"
            "=== broken.json ===\n%s\n"
            % (data_date(), json.dumps(scraped, ensure_ascii=False),
               json.dumps(broken or [], ensure_ascii=False)))


def sanitize(text):
    """Strip fences / any document wrapper; guarantee a SUBJECT and a full <div>."""
    text = FENCE_RE.sub("", text.strip()).strip()
    text = re.sub(r"(?is)<!DOCTYPE[^>]*>", "", text)
    text = re.sub(r"(?is)<head\b.*?</head>", "", text)
    text = re.sub(r"(?is)</?html[^>]*>", "", text)
    text = re.sub(r"(?is)</?body[^>]*>", "", text).strip()
    if not SUBJECT_RE.search(text[:600]):
        text = ("<!-- SUBJECT: digest \u2014 %s -->\n" % data_date()) + text
    if "<div" not in text.lower():
        raise ValueError("model output has no wrapper <div>")
    if not text.rstrip().endswith("</div>"):
        raise ValueError("model output looks truncated (does not end with </div>)")
    return text


def _fallback_body(title, detail):
    return ("<!-- SUBJECT: digest failed \u2014 %s -->\n"
            '<div style="max-width:640px;font-family:-apple-system,\'Segoe UI\','
            'Roboto,Helvetica,Arial,sans-serif;font-size:14px;color:#1f2328;">'
            '<div style="background-color:#b00020;color:#ffffff;font-weight:700;'
            'padding:8px 12px;border-radius:4px;">%s</div>'
            '<p style="color:#4a545c;">%s</p></div>' % (data_date(), title, detail))


def write_failure(reason, raw=None):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "digest.html").write_text(
        _fallback_body("Digest step failed", reason), encoding="utf-8")
    note = "digest.py failure for %s\nreason: %s\n" % (data_date(), reason)
    if raw:
        note += "\n----- raw model output -----\n" + raw[:20000]
    (OUTPUT_DIR / "digest.error.txt").write_text(note, encoding="utf-8")
    print("FAILED:", reason, file=sys.stderr)


def main():
    scraped, broken = read_inputs()
    if not scraped:
        write_failure("No scraped.json for %s, so no digest was produced." % data_date())
        return 0

    system = build_system()
    user = build_user_message(scraped, broken)

    raw = None
    try:
        raw = reasoner.complete(system, user, DIGEST_PLATFORM, DIGEST_MODEL,
                                max_tokens=DIGEST_MAX_TOKENS,
                                session="digest-%s" % data_date())
        html = sanitize(raw)
    except Exception as exc:  # noqa: BLE001 - surface any failure
        write_failure("%s: %s" % (type(exc).__name__, exc), raw)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "digest.html").write_text(html, encoding="utf-8")
    print("wrote %s (%d chars, %d listings, system %d chars, %s/%s)"
          % (OUTPUT_DIR / "digest.html", len(html), len(scraped), len(system),
             DIGEST_PLATFORM, DIGEST_MODEL))
    return 0


if __name__ == "__main__":
    # Optional: `python digest.py 2026-09-26` runs against a specific dated
    # output folder instead of today's (useful for re-runs and testing).
    for arg in sys.argv[1:]:
        if DATE_RE.match(arg):
            import config
            OUTPUT_DIR = config.BASE_DIR / "output" / arg
    sys.exit(main())
