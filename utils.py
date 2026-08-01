import json

def json_dump(obj, path):
    with open(path, 'w') as fp:
        json.dump(obj, fp, indent=4)