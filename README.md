# Simplify Filter

Automated triage for the daily internship digest from [SWElist](https://swelist.com).

The first part of this script the digest email over IMAP, parses out each listing, drops non-matches against a keyword blacklist and whitelist, and scrapes the remaining Simplify postings for requirements, qualifications, location, term, and salary. The result is written as structured JSON. 

The user then has the option to schedule an LLM task that evaluates those listings into an HTML digest saved locally, which the second half of this script can email out.

## Requirements

- Python 3.11+
- A Gmail account with 2-Step Verification enabled

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in:

```
GMAIL_USER=you@gmail.com
APP_PASSWORD=your app password
```

Generate the app password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

Copy `filters/blacklist.example.txt` and `filters/whitelist.example.txt` to `blacklist.txt` and `whitelist.txt`, then edit them. One keyword per line, matched case-insensitively against the position title. An empty whitelist matches everything.

## Running

```
python main.py      # retrieve, filter, scrape
python sender.py    # email the digest
```

Each module also runs standalone against the previous stage's output, which is useful for debugging a single step.

## Scheduling

Three tasks must run in sequence, with enough separation for each to finish before the next begins.

| Order | Task | Purpose |
|---|---|---|
| 1 | `main.py` | Produces `scraped.json` |
| 2 | LLM scheduled task | Reads the JSON, writes `digest.html` |
| 3 | `sender.py` | Emails the digest |

On Windows, point Task Scheduler at `.venv\Scripts\pythonw.exe` with the script name as the argument and the project root as **Start in**. Set a timeout under task settings; tasks can otherwise report "Running" indefinitely and block the following day's run.

## Output

Everything for a given day is written to `output/YYYY-MM-DD/`:

| File | Written by | Contents |
|---|---|---|
| `scraped.json` | `scraper.py` | Full listing details |
| `broken.json` | `scraper.py` | Listings whose scrape failed |
| `digest.html` | LLM task | Finished email body |

## LLM task prompt

The prompt is not included in this repository. It must specify at minimum:

- Read `scraped.json` from the current date's folder in `output/`. Fields vary between listings; any key may be absent.
- Read `broken.json` if present. These listings have a company, position, and link but no requirements, and should be surfaced separately rather than dropped.
- Write the result to `digest.html` in the same folder, overwriting any existing file.
- Output only body-level HTML — no `<!DOCTYPE>`, `<html>`, `<head>`, or `<body>` tags. `sender.py` sends the file contents directly as an email body.
- Use inline `style` attributes only. `<style>` blocks and external stylesheets are stripped by most email clients.
- Include `<!-- SUBJECT: ... -->` as the first line. `sender.py` reads the subject line from this comment and falls back to a generic dated subject if it is missing.

## Layout

```
config.py      credentials, paths, filter lists
retriever.py   IMAP retrieval
parser.py      listing extraction
filter.py      keyword filtering
scraper.py     posting detail scraping
sender.py      SMTP delivery
utils.py       shared helpers
```