# Simplify Filter

Automated triage for the daily internship digest from [SWElist](https://swelist.com).

The first part of this script the digest email over IMAP, parses out each listing, drops non-matches against a keyword blacklist and whitelist, and scrapes the remaining Simplify postings for requirements, qualifications, location, term, and salary. The result is written as structured JSON. 

The pipeline then evaluates those listings against a fit profile with an LLM and emails the resulting HTML digest — all in a single run.

## Requirements

- **Python 3.14** — this is what the server runs. Build the venv against it
  explicitly if you have several versions installed: a venv hardcodes an absolute
  path to its base interpreter, so one created against the wrong Python will not
  run where the scheduled tasks do.
- A Gmail account with 2-Step Verification enabled

### How the scraper reads a posting

`scraper.py` fetches each posting page and reads the structured JSON Simplify's
Next.js page embeds at `__NEXT_DATA__ → props.pageProps.jobPosting`. Every field
is read by name, so a missing field produces a missing key rather than shifting
every later value into the wrong one. If that tag is ever absent, the scraper
falls back to the page's schema.org JSON-LD `JobPosting` (a reduced mapping) and
records the fallback in `unclassified.json`, so a silent degradation shows up as
a visible warning.

This replaced an older scraper that parsed trafilatura's flattened text
positionally — that approach broke when Simplify changed its page layout on
2026-09-18. The old zstd workaround is no longer needed for scraping, though
`config.py` still pins `Accept-Encoding` harmlessly.

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in:

```
IMAP_USER=you@gmail.com
IMAP_PASSWORD=your app password
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your app password
DIGEST_RECIPIENT=where@to.send
OPENCODE_GO_KEY=your opencode go api key
```

Generate the app password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

Copy `filters/blacklist.example.txt` and `filters/whitelist.example.txt` to `blacklist.txt` and `whitelist.txt`, then edit them. One keyword per line, matched case-insensitively against the position title. An empty whitelist matches everything.

## Running

```
python main.py      # retrieve, filter, scrape, digest, send
```

`main.py` runs the whole pipeline in one process. Every stage still runs
standalone for debugging — `python digest.py` (or `python digest.py 2026-09-26`
for a specific day), `python sender.py` to re-send, and so on.

## Scheduling

One task runs everything:

| Task | Purpose |
|---|---|
| `main.py` | retrieve -> filter -> scrape -> digest -> send |

On Windows, point Task Scheduler at `.venv\Scripts\pythonw.exe` with `main.py` as
the argument and the project root as **Start in**. The digest step calls a
reasoning model, so allow a generous timeout (several minutes) under task
settings; tasks can otherwise report "Running" indefinitely and block the
following day's run.

## Output

Everything for a given day is written to `output/YYYY-MM-DD/`:

| File | Written by | Contents |
|---|---|---|
| `scraped.json` | `scraper.py` | Full listing details |
| `broken.json` | `scraper.py` | Listings whose scrape failed |
| `unclassified.json` | `scraper.py` | JSON-LD fallbacks + unrecognized enum codes (only written when non-empty) |
| `digest.html` | `digest.py` | Finished email body |

## The digest step

`digest.py` composes a system message from five documents and sends it with
today's `scraped.json` (+ `broken.json`), then writes `digest.html`; `sender.py`
emails it.

| Document | Purpose |
|---|---|
| `prompt/task.md` | run mechanics + email structure and HTML |
| `prompt/criteria.md` | how to judge fit |
| `profile/resume.txt` | the resume, as plain text |
| `profile/self_assessment.md` | calibrated skill levels |
| `profile/preferences.md` | eligibility, ranked locations, roles, timing, comp |

Edit those files, not a single monolith. Copy each `profile/*.example.*` to its
real name (`resume.txt`, `preferences.md`, `self_assessment.md`) and fill it in.

Platform and model live in `.env` (see the table at the top of `reasoner.py`):

```
DIGEST_PLATFORM=opencode-go
DIGEST_MODEL=deepseek-v4.1-flash
OPENCODE_GO_KEY=...
DIGEST_MAX_TOKENS=40000
```

Switching model or platform is a `.env` change only. Reasoning models spend part
of `DIGEST_MAX_TOKENS` on hidden reasoning; if the answer is truncated
(`finish_reason=length`) `reasoner.py` doubles the budget and retries. On failure
`digest.py` writes a visible "digest failed" body plus `digest.error.txt`.

## Layout

```
prompt/        task.md + criteria.md (the run's instructions)
profile/       resume.txt + preferences.md + self_assessment.md
config.py      credentials, paths, filter lists, digest settings
retriever.py   IMAP retrieval
parser.py      listing extraction
filter.py      keyword filtering
scraper.py     posting detail scraping
digest.py      LLM evaluation -> digest.html
reasoner.py    platform-agnostic model client
sender.py      SMTP delivery
utils.py       shared helpers
```