# Task — internship digest

Once per day, read the inline `scraped.json` (and `broken.json`), evaluate every
listing against the candidate profile (`profile/`) and the rules in
`criteria.md`, and produce a ranked, categorized HTML digest.

You are running non-interactively with **no file access**. Everything you need is
inline (today's date, then `scraped.json`, then `broken.json`). Return the
finished email **body only** — a single wrapper `<div>`, nothing before or after,
no code fences.

## Input handling

`scraped.json` is a list of listing objects. `Company`, `Position`, `Link` are
always present; every other key may be absent. Possible fields: `Company`,
`Position`, `Link`, `Term`, `Activity`, `Listing Date`, `Updated Date`,
`Deadline`, `Brief Company Description`, `Full Company Description`, `Salary`,
`Additional Compensation`, `H1B`, `Job Location`, `More Locations`,
`Workplace Model`, `Degree Levels`, `Citizenship / Clearance`, `Notes` (list),
`Requirements` (list), `Responsibilities` (list), `Desired Qualifications`
(list), `Skills`, `Functions`, `Company Size`, `Company Stage`, `Total Funding`,
`Headquarters`, `Founded`.

- **Never infer a value that isn't there.** Missing → unknown → write "not listed".
- `Requirements` absent or empty → fall back to `Desired Qualifications`, rank
  normally, and note in the Verify line that no hard requirements were listed.
  Only route to *Needs manual check* if both arrays are missing.
- Company metadata (`Total Funding`, `Company Stage`, `Headquarters`) is scraped
  and sometimes wrong — don't reason from it.
- **Every listing must appear exactly once** in the email — ranked, filtered,
  needs-check, or Scraper Issues — except inactive listings. Collapsing
  near-duplicates (see Digest discipline) still counts.

## Hard exclusion
Any listing whose `Activity` is `INACTIVE` → **drop completely**. Do not list it
anywhere; report only a count at the end: "N inactive listings dropped."

## Ranked sections — grouped by term, chronological
Group ranked listings by the `Term` value, in chronological order:

```
Fall 2026  →  Winter 2027  →  Spring 2027  →  Summer 2027  →  Fall 2027  →  ...
```

- Winter sits **between** the prior Fall and the following Spring — its own section.
- `Term` lists more than one term → file under the **earliest**.
- Title names a different term than `Term` → **trust `Term`** (the structured value).

Then, after all season sections, in this order:
- **Term unclear / year-round / generic "Internship"**
- **Part-Time**
- **Full-time, New Grad, or Early Career** — only if open to [GRADUATION DATE] graduates or not requiring current full-time enrollment.
- **Term already started or passed** — a season term whose start is in the past; still ranked and clickable. (If a hard requirement also applies, route on the hard blocker instead.)

Any term value not covered → *Term unclear*. Never invent a ranked section for an
unrecognized term.

**Label sections with letters assigned sequentially in the order they actually
appear — A, B, C… skipping the letter I.** Don't reserve fixed letters for
sections you aren't printing.

**Ordering within a ranked section:** (1) location tier, best first, then
(2) strength of skill match (`criteria.md`). Role type never affects ordering.

## Filtered sections — grouped by reason
In this order, skipping any with no entries:
- **Skills gap — close** (first in the filtered block — near-misses worth reading)
- **Skills gap — out of reach**
- **Hard requirement not met**
- **Requires current Master's or PhD enrollment**
- **Location mismatch**
- **Wrong field entirely**
- **IT support / help desk**
- **Needs manual check**

If a listing's reason is specific and fits none of these, create a new category
named after that reason (a one-listing category is fine). When a listing fits
more than one filtered category, **hard blockers win**.

## Scraper Issues — the last section
Anything from `broken.json`: company, position, link, and a short note on why the
scrape failed. Keep it visually separate from the filtered block.

## Per-listing content
**Ranked entries** — four elements, each on its own line:
1. Company — Position (this is the clickable link)
2. Metadata: **location tier** · location · workplace model · salary if listed · deadline if listed
3. **Why it fits:** one sentence naming what in the Requirements matches the real skills, and at what level
4. **Verify:** only if something genuinely needs checking — relocation for Tier 3 and below, enrollment/graduation gates, work authorization for Canada, a GPA cutoff near his, or no Requirements listed. Omit entirely when nothing needs checking. Never flag US citizenship or visa sponsorship.

**Filtered entries** — one row each: Company — Position (clickable), then the
reason in ≤12 words.

Always include company, position, and link, even for filtered listings.

## Digest discipline
- Never quote or summarize `Full Company Description`.
- Don't restate the responsibilities list — one clause on what the role does, and only if the title doesn't already make it obvious.
- Don't repeat the same requirement across listings; mention a recurring pattern once in the footer instead.
- **Collapse near-duplicate postings** (same company + role + requirements, differing only by location/deadline) into one entry: name every location, use the best tier for ordering, and note the other cities/deadlines in Verify.

## Output
Write the finished body as your response. First line:

```
<!-- SUBJECT: Internship digest — YYYY-MM-DD — R ranked, F filtered -->
```

with the real date and counts **as they appear in the email after collapsing**.
Body markup only — no `<!DOCTYPE>`, `<html>`, `<head>`, or `<body>`.

## HTML formatting (strict)
1. Link text is the company and position — **never the URL**.
2. All styling is inline `style=""` — no `<style>` blocks, classes, or media queries.
3. No JavaScript, external images, web fonts, or `<hr>` separators.
4. Never emit markdown (`**bold**`, `---`, `#`) — it renders literally.
5. Every section header is a colored band.
6. Width ≤ 640px; one piece of information per line.

Use this skeleton exactly:

```html
<div style="max-width:640px;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:14px;line-height:1.5;color:#1f2328;background-color:#ffffff;padding:16px;">

  <div style="font-size:18px;font-weight:700;color:#1f2328;margin:0 0 4px;">Internship digest — 2026-07-29</div>
  <div style="font-size:13px;color:#5f6b73;margin:0 0 24px;">2 ranked · 16 filtered · 2 inactive dropped</div>

  <div style="background-color:#0b5cad;color:#ffffff;font-size:15px;font-weight:700;padding:8px 12px;border-radius:4px;margin:28px 0 12px;">A. Fall 2026</div>

  <div style="border-left:4px solid #0b5cad;background-color:#f6f9fc;padding:10px 14px;margin:0 0 12px;">
    <a href="URL" style="font-size:15px;font-weight:700;color:#0b5cad;text-decoration:none;">Apple — Applied Data Solutions Program Intern</a>
    <div style="font-size:13px;color:#5f6b73;margin:5px 0 0;">Tier 2 · Austin, TX · In Person</div>
    <div style="margin:7px 0 0;"><span style="font-weight:600;">Why it fits:</span> Requirements ask for proficiency in one language including Python, plus data structures.</div>
    <div style="font-size:13px;color:#8a5a00;margin:7px 0 0;"><span style="font-weight:600;">Verify:</span> relocation to Austin — not LA, Bay Area, or remote.</div>
  </div>

  <div style="background-color:#eceff1;color:#37474f;font-size:14px;font-weight:700;padding:7px 12px;border-radius:4px;margin:28px 0 8px;">H. Hard requirement not met</div>

  <div style="padding:6px 2px;border-bottom:1px solid #eceff1;">
    <a href="URL" style="font-weight:600;color:#37474f;text-decoration:none;">Bosch Home Comfort — ADAS Software Engineer Intern</a>
    <span style="color:#78868f;"> — GPA cutoff 3.0 stated</span>
  </div>

  <div style="border:1px solid #dfe3e6;border-radius:4px;padding:12px 14px;margin:28px 0 0;font-size:13px;color:#4a545c;">
    <span style="font-weight:600;">Pattern notes:</span> …
  </div>

</div>
```

Colors: blue `#0b5cad` for ranked sections and their card borders; gray
`#eceff1`/`#37474f` for filtered bands; amber `#8a5a00` for Verify lines; muted
gray `#5f6b73`/`#78868f` for metadata and reasons. `margin:28px` above every
section header, `12px` between ranked cards, `6px` per filtered row.

The Scraper Issues section uses an amber band so it doesn't read as a fit category:

```html
<div style="background-color:#fff4e0;color:#8a5a00;font-size:14px;font-weight:700;padding:7px 12px;border-radius:4px;margin:36px 0 8px;">Scraper Issues — data problems, not fit judgments</div>
```
