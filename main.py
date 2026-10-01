### main.py -- the whole daily pipeline in one process:
###   retrieve -> parse -> filter -> scrape -> digest -> send
###
### One scheduled task runs all of it. Every stage still runs standalone for
### debugging (retriever.py, parser.py, filter.py, scraper.py, digest.py,
### sender.py). `python main.py --no-send` runs everything except the email.
###
### Under pythonw.exe there is no console, so every run is logged to
### logs/run-YYYY-MM-DD.log. If the run fails (e.g. SWElist sent no digest that
### day) a short "No digest today" notice is emailed instead of going silent.

import sys
import traceback
from datetime import date, datetime

try:
    import urllib3.util.request as _u3
    _u3.ACCEPT_ENCODING = "gzip,deflate"
except ImportError:
    pass

from config import OUTPUT_DIR, BASE_DIR
from utils import json_dump
from retriever import retrieve_email
from parser import parse_email
from filter import filter
from scraper import scrape_all, for_digest
from digest import main as run_digest
from sender import send_digest, send_notice


class _Tee:
    """Write to the log file and, when there is one, the console."""

    def __init__(self, *streams):
        self._streams = streams

    def write(self, text):
        for stream in self._streams:
            try:
                stream.write(text)
            except Exception:
                pass
        return len(text)

    def flush(self):
        for stream in self._streams:
            try:
                stream.flush()
            except Exception:
                pass


def run(send=True):
    email = retrieve_email()
    print(email.date, email.subject)

    listings = parse_email(email.html)
    print(len(listings), "listings parsed")

    filtered = filter(listings)
    print(len(filtered), "listings after filtering")

    scraped = scrape_all(filtered, detailed=True)
    json_dump(for_digest(scraped), OUTPUT_DIR / "scraped.json")
    print(len(scraped), "scraped ->", OUTPUT_DIR / "scraped.json")

    rc = run_digest()
    if rc != 0:
        print("digest step failed (rc=%d)" % rc)

    if send:
        send_digest()
    else:
        print("--no-send: email not sent")


if __name__ == "__main__":
    send = "--no-send" not in sys.argv

    logdir = BASE_DIR / "logs"
    logdir.mkdir(exist_ok=True)
    log = open(logdir / ("run-%s.log" % date.today().isoformat()), "a", encoding="utf-8")

    streams = [log]
    if sys.stdout is not None:
        streams.append(sys.stdout)
    sys.stdout = sys.stderr = _Tee(*streams)

    failed = False
    print("=== run start %s (send=%s) ===" % (datetime.now().isoformat(), send))
    try:
        run(send=send)
        print("=== run complete %s ===" % datetime.now().isoformat())
    except Exception as exc:
        failed = True
        traceback.print_exc()
        print("=== run FAILED %s ===" % datetime.now().isoformat())
        if send:
            try:
                send_notice("No digest today - " + date.today().isoformat(),
                            "No digest was produced today.\n\nReason: %s: %s"
                            % (type(exc).__name__, exc))
            except Exception:
                traceback.print_exc()
    finally:
        log.close()
    sys.exit(1 if failed else 0)
