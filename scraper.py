### scrapes each Simplify posting into structured JSON for the LLM task to read
###
### Data source: the posting page's embedded Next.js payload --
###   <script id="__NEXT_DATA__" type="application/json">
###     -> props.pageProps.jobPosting
### If that tag is ever absent (e.g. Simplify migrates to the App Router), we fall
### back to the page's schema.org JSON-LD JobPosting and RECORD that we did, so a
### silent degradation shows up as a visible warning instead of a week of quietly
### wrong digests.
###
### Unlike the previous scraper this never parses extracted prose. Every field is
### read by name from a structured object, so a missing field produces a missing
### key instead of shifting every later value into the wrong one.

import gzip
import json
import re
import zlib
from datetime import datetime
from urllib.request import Request, urlopen

from config import OUTPUT_DIR
from utils import json_dump, json_load

# The only line that differs between the internship and grad-job apps.
FEED = "intern"          # "intern" | "grad"

UA = "Mozilla/5.0 (compatible; SimplifyDigest/1.0)"
TIMEOUT = 30

# ---------------------------------------------------------------- enums
# Observed directly in Simplify's payload and cross-checked against the rendered
# chips. Unknown codes are passed through AND logged, never silently dropped.
SEASON_ENUM = {1: "Winter", 2: "Spring", 3: "Summer", 4: "Fall"}
TYPE_ENUM   = {1: "Internship", 2: "Full-Time", 3: "Part-Time", 4: "Contract"}
PERIOD_ENUM = {1: "hr", 2: "month", 3: "week", 4: "year"}
DEGREE_ENUM = {1: "Bachelor's", 2: "Master's", 5: "PhD", 9: "Bootcamp",
               13: "Bachelor of Science (BS)"}

UNKNOWN = {"degree": set(), "type": set(), "period": set(), "season": set()}

SEASON_RE = re.compile(r"\b(Winter|Spring|Summer|Fall)\s+\d{4}\b")
TAG_RE = re.compile(r"<[^>]+>")
NEXT_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
LD_RE = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.S)


# ---------------------------------------------------------------- fetch
def fetch_html(url):
    req = Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})
    with urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        enc = (resp.headers.get("Content-Encoding") or "").lower()
    if enc == "gzip":
        raw = gzip.decompress(raw)
    elif enc == "deflate":
        raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw.decode("utf-8", "replace")


def extract_jobposting(html):
    """Return (data_dict, source) where source is 'next' | 'ldjson' | 'missing'.
    'next' data is Simplify's own jobPosting object; 'ldjson' data is a schema.org
    JobPosting and is mapped by build_post_ldjson instead of build_post."""
    m = NEXT_RE.search(html)
    if m:
        try:
            jp = json.loads(m.group(1)).get("props", {}).get("pageProps", {}).get("jobPosting")
            if jp:
                return jp, "next"
        except (ValueError, AttributeError):
            pass
    for m in LD_RE.finditer(html):
        try:
            obj = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(obj, list):
            obj = next((o for o in obj if isinstance(o, dict)), None)
        if isinstance(obj, dict) and "JobPosting" in str(obj.get("@type", "")):
            return obj, "ldjson"
    return None, "missing"


# ---------------------------------------------------------------- helpers
def strip_html(s):
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", s or "")).strip()


def _money(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    return "${:,}".format(int(x)) if x == int(x) else "${:,.2f}".format(x)


def _date(iso):
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", ""))
    except ValueError:
        return str(iso)
    return "%d/%d/%d" % (dt.month, dt.day, dt.year)


def _company(jp):
    return (jp.get("job") or {}).get("company") or {}


def fmt_seasons(jp):
    out = []
    for s in (jp.get("seasons") or []):
        # payload gives [[season, year], ...]; tolerate {"value": [season, year]}
        v = s.get("value") if isinstance(s, dict) else s
        if not isinstance(v, (list, tuple)) or len(v) < 2:
            continue
        name = SEASON_ENUM.get(v[0])
        if name is None:
            UNKNOWN["season"].add(v[0])
            continue
        out.append("%s %d" % (name, v[1]))
    return out


def fmt_salary(jp):
    lo, hi, per = jp.get("min_salary"), jp.get("max_salary"), jp.get("salary_period")
    if lo is None and hi is None:
        return "No salary listed"
    unit = PERIOD_ENUM.get(per)
    if unit is None and per is not None:
        UNKNOWN["period"].add(per)
        unit = "period%s" % per
    suffix = {"hr": "/hr", "month": "/month", "week": "/week", "year": "/yr"}.get(unit, "")
    if lo is not None and hi is not None and lo != hi:
        body = "%s - %s" % (_money(lo), _money(hi))
    else:
        body = _money(lo if lo is not None else hi)
    return (body + suffix).strip()


def fmt_degrees(jp):
    out = []
    for d in (jp.get("degrees") or []):
        if d in DEGREE_ENUM:
            out.append(DEGREE_ENUM[d])
        else:
            UNKNOWN["degree"].add(d)
            out.append("Level %s" % d)
    return ", ".join(out)


def fmt_type(jp):
    t = (jp.get("job") or {}).get("type")
    if t is None:
        return None
    name = TYPE_ENUM.get(t)
    if name is None:
        UNKNOWN["type"].add(t)
        name = "Type %s" % t
    return name


def derive_workplace(jp):
    locs = [(l.get("value") or "") for l in (jp.get("locations") or [])]
    if any(l.lower().startswith("remote") for l in locs):
        return "Remote"
    info = (jp.get("additional_location_info") or "").lower()
    if "hybrid" in info:
        return "Hybrid"
    if any(w in info for w in ("on-site", "onsite", "on site", "in person", "in-person")):
        return "In Person"
    return None


def derive_citizenship(jp):
    """Best effort. The grad prompt only hard-blocks on 'clearance'."""
    blob = " ".join(filter(None, [
        strip_html(jp.get("description")),
        strip_html(jp.get("additional_location_info")),
        " ".join(jp.get("requirements") or []),
        " ".join(jp.get("responsibilities") or []),
    ])).lower()
    out = []
    if "clearance" in blob:
        out.append("Clearance Required")
    if any(w in blob for w in ("citizenship", "permanent residen", "asylee", "refugee status")):
        out.append("US Citizenship Required")
    if "export control" in blob or "itar" in blob:
        out.append("ITAR / export-controlled")
    return ", ".join(out) or None


def _intern_term(jp, seasons):
    if FEED == "grad":
        return fmt_type(jp)
    term = ", ".join(seasons) if seasons else None
    if not term:
        m = SEASON_RE.search(str(jp.get("subtitles") or ""))
        if m:
            term = m.group(0)
    return term


# ---------------------------------------------------------------- mapping
# Primary: Simplify's own structured object.
def build_post(entry, jp, source):
    post = {"Company": entry.get("Company"), "Position": entry.get("Position"),
            "Link": entry.get("Link")}
    company = _company(jp)
    if company.get("name"):
        post["Company"] = company["name"]
    if jp.get("title"):
        post["Position"] = jp["title"]

    seasons = fmt_seasons(jp)
    employment = fmt_type(jp)
    term = _intern_term(jp, seasons)
    if term:
        post["Term"] = term
    if seasons:
        post["Seasons"] = ", ".join(seasons)
    if employment:
        post["Employment Type"] = employment

    if jp.get("active") is False:
        post["Activity"] = "INACTIVE"

    ld = _date((jp.get("date_display") or {}).get("date") or jp.get("start_date"))
    if ld:
        post["Listing Date"] = "Posted on %s" % ld
    if jp.get("updated_date"):
        post["Updated Date"] = "Updated on %s" % _date(jp["updated_date"])
    if jp.get("end_date"):
        post["Deadline"] = "Deadline %s" % _date(jp["end_date"])

    if company.get("short_description"):
        post["Brief Company Description"] = strip_html(company["short_description"])
    if company.get("description"):
        post["Full Company Description"] = strip_html(company["description"])
    post["Salary"] = fmt_salary(jp)
    if jp.get("additional_salary_info"):
        post["Additional Compensation"] = strip_html(jp["additional_salary_info"])

    h1b = jp.get("sponsors_h1b")
    if h1b is not None:
        post["H1B"] = "H1B Sponsorship Available" if h1b else "No H1B Sponsorship"

    locs = [l.get("value") for l in (jp.get("locations") or []) if l.get("value")]
    if locs:
        post["Job Location"] = locs[0]
        if len(locs) > 1:
            post["More Locations"] = "More locations: " + " | ".join(locs[1:])
    wp = derive_workplace(jp)
    if wp:
        post["Workplace Model"] = wp

    degrees = fmt_degrees(jp)
    if degrees:
        post["Degree Levels"] = degrees
    cit = derive_citizenship(jp)
    if cit:
        post["Citizenship / Clearance"] = cit

    if jp.get("requirements"):
        post["Requirements"] = [strip_html(r) for r in jp["requirements"] if strip_html(r)]
    if jp.get("responsibilities"):
        post["Responsibilities"] = [strip_html(r) for r in jp["responsibilities"] if strip_html(r)]
    if jp.get("desirable"):
        post["Desired Qualifications"] = [strip_html(r) for r in jp["desirable"] if strip_html(r)]

    skills = [s.get("name") for s in (jp.get("skills") or []) if s.get("name")]
    if skills:
        post["Skills"] = ", ".join(skills)
    functions = [f.get("title") for f in (jp.get("functions") or []) if f.get("title")]
    if functions:
        post["Functions"] = ", ".join(functions)

    notes = []
    if jp.get("additional_location_info"):
        notes.append(strip_html(jp["additional_location_info"]))
    if notes:
        post["Notes"] = notes

    if company.get("company_size"):
        post["Company Size"] = company["company_size"]
    if company.get("funding_stage"):
        post["Company Stage"] = company["funding_stage"]
    if company.get("funding_total"):
        post["Total Funding"] = _money(company["funding_total"])
    hq = (company.get("harmonic_location") or {}).get("address_formatted")
    if hq:
        post["Headquarters"] = hq
    if company.get("year_founded"):
        post["Founded"] = str(company["year_founded"])

    return post


# Fallback: schema.org JobPosting JSON-LD. Deliberately partial, but useful.
def _ld_location(obj):
    loc = obj.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    if not isinstance(loc, dict):
        return None
    addr = loc.get("address")
    if isinstance(addr, str):
        return addr
    if not isinstance(addr, dict):
        return None
    country = addr.get("addressCountry")
    if isinstance(country, dict):
        country = country.get("name")
    parts = [addr.get("addressLocality"), addr.get("addressRegion"), country]
    return ", ".join(str(p) for p in parts if p and str(p).upper() != "N/A") or None


def build_post_ldjson(entry, obj):
    post = {"Company": entry.get("Company"), "Position": entry.get("Position"),
            "Link": entry.get("Link")}
    org = obj.get("hiringOrganization")
    if isinstance(org, dict) and org.get("name"):
        post["Company"] = org["name"]
    if obj.get("title"):
        post["Position"] = obj["title"]
    if obj.get("datePosted"):
        post["Listing Date"] = "Posted on %s" % _date(obj["datePosted"])
    if obj.get("validThrough"):
        post["Deadline"] = "Deadline %s" % _date(obj["validThrough"])
    et = obj.get("employmentType")
    if et:
        et = et if isinstance(et, str) else ", ".join(map(str, et))
        et = {"FULL_TIME": "Full-Time", "PART_TIME": "Part-Time",
              "CONTRACTOR": "Contract", "INTERN": "Internship",
              "TEMPORARY": "Temporary"}.get(et.upper(), et)
        post["Employment Type"] = et
        if FEED == "grad":
            post["Term"] = et
    loc = _ld_location(obj)
    if loc:
        post["Job Location"] = loc
    bs = obj.get("baseSalary")
    val = bs.get("value") if isinstance(bs, dict) else None
    if isinstance(val, dict) and (val.get("minValue") or val.get("maxValue")):
        unit = (val.get("unitText") or "").lower()
        suffix = {"hour": "/hr", "hourly": "/hr", "month": "/month",
                  "year": "/yr", "annual": "/yr"}.get(unit, "")
        lo, hi = val.get("minValue"), val.get("maxValue")
        if lo and hi and lo != hi:
            post["Salary"] = "%s - %s%s" % (_money(lo), _money(hi), suffix)
        else:
            post["Salary"] = "%s%s" % (_money(lo or hi), suffix)
    er = obj.get("educationRequirements")
    if isinstance(er, list):
        er = er[0] if er else None
    if isinstance(er, dict):
        er = er.get("educationalLevel") or er.get("name")
    if isinstance(er, dict):
        er = er.get("name")
    if er:
        post["Degree Levels"] = ", ".join(map(str, er)) if isinstance(er, list) else str(er)
    desc = obj.get("description") or ""
    bullets = [strip_html(b) for b in re.findall(r"<li[^>]*>(.*?)</li>", desc, re.S)]
    bullets = [b for b in bullets if b]
    if bullets:
        post["Requirements"] = bullets
    if desc:
        post["Notes"] = ["Parsed from JSON-LD fallback (__NEXT_DATA__ was absent)"]
    return {k: v for k, v in post.items() if v}


# ---------------------------------------------------------------- runner
def scrape(post_entry):
    html = fetch_html(post_entry["Link"])
    data, source = extract_jobposting(html)
    if data is None:
        raise ValueError("no __NEXT_DATA__ jobPosting and no JSON-LD JobPosting")
    if source == "ldjson":
        return build_post_ldjson(post_entry, data), data, source
    return build_post(post_entry, data, source), data, source


# The digest prompt is told never to quote Full Company Description, but it is
# still ~23% of scraped.json and costs roughly 12k tokens every run. Keep it in
# detailed_scrape/<n>.json, strip it from the aggregate the LLM task reads.
DIGEST_OMIT = ("Full Company Description",)


def for_digest(posts):
    return [{k: v for k, v in p.items() if k not in DIGEST_OMIT} for p in posts]


def scrape_all(filtered_list, detailed=False):
    scraped, broken, fallbacks = [], [], []
    out_dir = None
    if detailed:
        out_dir = OUTPUT_DIR / "detailed_scrape"
        out_dir.mkdir(parents=True, exist_ok=True)

    for i, entry in enumerate(filtered_list):
        print(i, entry.get("Company"), entry.get("Position"), sep=" | ")
        try:
            post, data, source = scrape(entry)
        except Exception as exc:
            print("    broken:", exc)
            broken.append(dict(entry, Error=str(exc)))
            continue
        scraped.append(post)
        if source == "ldjson":
            # Loud, not silent: the primary structured source vanished.
            print("    !! FELL BACK TO JSON-LD for", entry.get("Company"))
            fallbacks.append({"Company": post.get("Company"), "Position": post.get("Position"),
                              "Link": post.get("Link"), "Note": "parsed from JSON-LD fallback"})
        if detailed:
            json_dump(post, out_dir / ("%d.json" % i))
            json_dump(data, out_dir / ("%d.raw.json" % i))

    if broken:
        json_dump(broken, OUTPUT_DIR / "broken.json")

    unknown = {k: sorted(v) for k, v in UNKNOWN.items() if v}
    if fallbacks or unknown:
        json_dump({"fallbacks": fallbacks, "unknown_enums": unknown},
                  OUTPUT_DIR / "unclassified.json")

    print("\n%d scraped, %d broken, %d JSON-LD fallback(s)"
          % (len(scraped), len(broken), len(fallbacks)))
    if unknown:
        print("unknown enum codes:", unknown)
    return scraped


def _test(n):
    """python scraper.py --test N  -> map N live postings, write nothing."""
    seed = json_load(OUTPUT_DIR / "scraped.json")
    for entry in seed[:n]:
        try:
            post, _data, source = scrape(entry)
            print("\n===", entry.get("Company"), "|", entry.get("Position"), "| source=", source)
            print(json.dumps(post, indent=2, ensure_ascii=False)[:1800])
        except Exception as exc:
            print("\n=== FAILED", entry.get("Link"), ":", exc)


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        _test(int(sys.argv[sys.argv.index("--test") + 1]) if len(sys.argv) > sys.argv.index("--test") + 1 else 5)
    else:
        filtered_list = json_load(OUTPUT_DIR / "filtered_list.json")
        scraped = scrape_all(filtered_list, detailed=True)
        json_dump(for_digest(scraped), OUTPUT_DIR / "scraped.json")
