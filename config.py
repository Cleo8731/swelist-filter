import os
import sys
from pathlib import Path
from datetime import date, timedelta

from dotenv import load_dotenv

# Python 3.14 bundles zstd, so urllib3 advertises zstd in its Accept-Encoding
# header. trafilatura can't decode a zstd response: fetch_url() returns the
# undecoded body and extract() then returns None, which blows up as an
# AttributeError on .splitlines(). main.py pins this too, but doing it here
# covers the standalone entry points (python scraper.py) as well.
import urllib3.util.request as _urllib3_request
_urllib3_request.ACCEPT_ENCODING = "gzip,deflate"

# Subjects and scraped text contain emoji, em dashes and middots. Windows'
# console defaults to cp1252 and print() dies on them with UnicodeEncodeError,
# which makes any console debugging run fail on its first print. Under
# pythonw.exe there is no stdout at all, hence the guard.
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass

# Anchor everything to this file's own location, not the working directory.
# Task Scheduler launches scripts with an unpredictable cwd, so Path.cwd()
# would resolve output/ and filters/ somewhere else entirely.
load_dotenv(override=True)

IMAP_HOST = "imap.gmail.com"
IMAP_USER = os.environ["IMAP_USER"]
IMAP_PASSWORD = os.environ["IMAP_PASSWORD"]

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
RECIPIENT = os.environ["DIGEST_RECIPIENT"]

DATE = date.today() - timedelta(days=0)

OUTPUT_DIR = Path.cwd() / 'output' / DATE.isoformat()

with open(Path.cwd() / 'filters' / 'blacklist.txt', encoding='utf-8') as fp:
    BLACKLIST = fp.read().splitlines()
with open(Path.cwd() / 'filters' / 'whitelist.txt', encoding='utf-8') as fp:
    WHITELIST = fp.read().splitlines()