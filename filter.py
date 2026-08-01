### keyword filter 
### takes full daily data structure and applies whitelist / blacklist filters
### returns and prints a more processed data structure to daily output folder for the parser
### note: case sensitivity?
### note: position or company separate lists?

from json import load

from config import OUTPUT_DIR, BLACKLIST, WHITELIST
from utils import json_dump

def blacklisted(entry):
    for keyword in BLACKLIST:
        if keyword.lower() in entry['Position'].lower():
            return True
    return False

def whitelisted(entry):
    if WHITELIST:
        for keyword in WHITELIST:
            if keyword.lower() in entry['Position'].lower():
                return True
        return False
    else:
        return True

def filter(full_list):
    filtered = []
    for entry in full_list:
        if not blacklisted(entry) and whitelisted(entry):
            filtered.append(entry)
    return filtered
    

if __name__ == "__main__":
    with open(OUTPUT_DIR / 'full_list.json') as fp:
        filtered = filter(load(fp))
    json_dump(filtered, OUTPUT_DIR / 'filtered_list.json')