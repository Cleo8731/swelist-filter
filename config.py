import os
import sys
from pathlib import Path
from datetime import date, timedelta

from dotenv import load_dotenv

# Python 3.14's urllib3 advertises zstd in Accept-Encoding. The scraper no longer
# uses trafilatura (it reads the page's embedded JSON), so a zstd response is no
# longer fatal — but the pin is kept for any other consumer, and guarded so that
# config does not hard-require urllib3.
try:
    import urllib3.util.request as _urllib3_request
    _urllib3_request.ACCEPT_ENCODING = "gzip,deflate"
except ImportError:
    pass

# Subjects and scraped text contain emoji, em dashes and middots. Windows'
# console defaults to cp1252 and print() dies on them with UnicodeEncodeError.
# Under pythonw.exe there is no stdout at all, hence the guard.
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass

# Anchor everything to this file's own location, not the working directory.
# Task Scheduler launches scripts with an unpredictable cwd, so Path.cwd()
# would resolve output/ and filters/ somewhere else entirely.
BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / '.env', override=True)

IMAP_HOST = "imap.gmail.com"
IMAP_USER = os.environ["IMAP_USER"]
IMAP_PASSWORD = os.environ["IMAP_PASSWORD"]

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
RECIPIENT = os.environ["DIGEST_RECIPIENT"]

# ---- LLM digest stage -------------------------------------------------------
# Platform + model come from .env so switching is a config change, not a code
# change. Key is a Bearer token; see reasoner.py for the platform table.
OPENCODE_GO_KEY = os.environ.get("OPENCODE_GO_KEY", "")
DIGEST_PLATFORM = os.environ.get("DIGEST_PLATFORM", "opencode-go")
DIGEST_MODEL = os.environ.get("DIGEST_MODEL", "deepseek-v4.1-flash")
# Reasoning models spend part of this on hidden reasoning, so keep it generous;
# reasoner.py doubles it automatically if the answer is truncated.
DIGEST_MAX_TOKENS = int(os.environ.get("DIGEST_MAX_TOKENS", "40000"))

DATE = date.today() - timedelta(days=0)

OUTPUT_DIR = BASE_DIR / 'output' / DATE.isoformat()

FILTER_DIR = BASE_DIR / 'filters'

with open(FILTER_DIR / 'blacklist.txt', encoding='utf-8') as fp:
    BLACKLIST = [line.strip() for line in fp.read().splitlines() if line.strip()]
with open(FILTER_DIR / 'whitelist.txt', encoding='utf-8') as fp:
    WHITELIST = [line.strip() for line in fp.read().splitlines() if line.strip()]
