import json


def json_dump(obj, path):
    # utf-8 on every write; Windows defaults to cp1252 and the scraped text
    # is full of em dashes and middots it can't encode.
    with open(path, 'w', encoding='utf-8') as fp:
        json.dump(obj, fp, indent=4, ensure_ascii=False)


def json_load(path):
    with open(path, encoding='utf-8') as fp:
        return json.load(fp)
