import os
from pathlib import Path
from datetime import date, timedelta

from dotenv import load_dotenv

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