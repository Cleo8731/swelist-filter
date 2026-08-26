import urllib3.util.request as _u3
_u3.ACCEPT_ENCODING = "gzip,deflate"

from config import OUTPUT_DIR
from utils import json_dump
from retriever import retrieve_email
from parser import parse_email
from filter import filter
from scraper import scrape_all, for_digest

if __name__=="__main__":
    email = retrieve_email()
    print(email.date, email.subject)
    listings = parse_email(email.html)
    filtered = filter(listings)
    scraped = scrape_all(filtered, detailed=True)
    json_dump(for_digest(scraped), OUTPUT_DIR / 'scraped.json')