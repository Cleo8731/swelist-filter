### scrapes simplify listing and puts it into a json file
# which Claude will then read and parse

from json import load
from copy import deepcopy

# config first: it pins urllib3's Accept-Encoding, which has to happen before
# trafilatura is imported, or fetch_url() comes back zstd-compressed and
# extract() returns None.
from config import OUTPUT_DIR
from utils import json_dump

from trafilatura import fetch_url, extract

def scrape(post):
    downloaded = fetch_url(post['Link'])
    result = extract(downloaded, favor_recall=True).splitlines()
    it = iter(result)

    def add(key, extra_fields=None):
        line = next(it)
        if extra_fields:
            for i in extra_fields:
                if i[-1].lower() in line.lower():
                    post[i[0]] = line
                    line = next(it)
        post[key] = line

    def skip(num):
        for _ in range(num):
            next(it)

    def skip_until(str, fallback=None):
        line = next(it)
        while str not in line:
            if line == fallback:
                return False
            line = next(it)
        return True

    def add_until(key, end, fallback=None):
        body = []
        line = next(it)
        while line != end:
            if line == fallback:
                return False
            body.append(line)
            line = next(it)
        post[key] = body
        return True

    add('Term', extra_fields=[('Activity','Inactive')])
    add('Brief Company Description', extra_fields=[('Listing Date', 'ted on '), ('Deadline',)])
    if '$' in post['Brief Company Description'] or 'salary' in post['Brief Company Description']:
        post['Salary'] = post.pop('Brief Company Description')
    else:
        add('Salary')
    add('Job Location', extra_fields=[('Additional Compensation', '+ '), ('H1B',)])
    if 'Additional Compensation' in post and 'more' in post['Additional Compensation']:
        post['Job Location'] = post.pop('Additional Compensation')
    add('Workplace Model', extra_fields=[('More Locations',), ('Relocation',)])
    if skip_until('Requirements', fallback='Responsibilities'):
        add_until('Requirements', 'Responsibilities', fallback='Company Size')

    try:
        add_until('Responsibilities', 'Company Size')
        post['Full Company Description'] = post['Responsibilities'].pop()
        try:
            split = post['Responsibilities'].index('Desired Qualifications')
            post['Desired Qualifications'] = post['Responsibilities'][split+1:]
            post['Responsibilities'] = post['Responsibilities'][:split]
        except ValueError:
            pass
    except StopIteration:
        it = iter(result)
        skip_until('Company Size')

    add('Company Size')
    for _ in range(4):
        add(next(it))

    #skip(1)
    #add_until('Company Insights According to Simplify', 'Help us improve and share your feedback! Did you find this helpful?')\
    #add_until('Benefits', 'Growth & Insights', )

    return result
# The digest prompt is told never to quote Full Company Description, but it is
# still ~23% of scraped.json and costs roughly 12k tokens every run to ship a
# field the model is forbidden to use. detailed_scrape/<n>.json keeps the full
# text, so strip it from the aggregate the LLM task actually reads.
# NOTE: that backup only exists when scrape_all runs with detailed=True.
DIGEST_OMIT = ('Full Company Description',)


def for_digest(posts):
    return [{k: v for k, v in p.items() if k not in DIGEST_OMIT} for p in posts]


def record_error(url, path):
    result = extract(fetch_url(url), favor_recall=True).splitlines()
    json_dump(result, path)


def scrape_all(filtered_list, detailed=False):
    scraped = []
    broken = []

    if detailed:
        out_dir = OUTPUT_DIR / 'detailed_scrape'
        out_dir.mkdir(exist_ok=True)

    for i, entry in enumerate(filtered_list):
        print(i, entry['Company'], entry['Position'], sep=' | ')
        #print("    ", entry['Link'])
        try:
            post = deepcopy(entry)
            result = scrape(post)
            scraped.append(post)
            if detailed:
                json_dump(result, out_dir / (str(i)+'.txt'))
                json_dump(post, out_dir / (str(i)+'.json'))
        except StopIteration:
            if detailed:
                result = extract(fetch_url(entry['Link']), favor_recall=True).splitlines()
                json_dump(result, out_dir / (str(i)+'.txt'))
            broken.append(entry)
            continue
        except IndexError:
            print(entry['Link'])
            record_error(entry['Link'], out_dir / (str(i)+'.txt'))

    if broken:
        json_dump(broken, OUTPUT_DIR / 'broken.json')

    return scraped


if __name__=="__main__":
    with open(OUTPUT_DIR / 'filtered_list.json', 'r') as filtered_list:
        scraped = scrape_all(load(filtered_list), detailed=False)
    json_dump(for_digest(scraped), OUTPUT_DIR / 'scraped.json')