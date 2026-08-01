### uses Beautiful Soup to parse into data structure
### data structure should include company, position, and simplify link
### data structure: list of dictionaries with 3 key-value pairs
### prints data structure to daily folder


from bs4 import BeautifulSoup
from config import OUTPUT_DIR
from utils import json_dump

def parse_email(email_html):
    
    soup = BeautifulSoup(email_html, 'html.parser')

    listings = []
    for entry in soup.find_all(class_="internship"):
        a = entry.find("a")
        listing = {
            "Company": entry.find("strong").text[:-1],
            "Link": a.get("href"),
            "Position": a.text
        }
        listings.append(listing)

    return listings
    

if __name__ == "__main__":
    with open(OUTPUT_DIR / 'full_email.html') as fp:
        listings = parse_email(fp)
    json_dump(listings, OUTPUT_DIR / 'full_list.json')