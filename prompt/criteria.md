# Evaluation criteria

How to decide *what each listing is*. Values come from `profile/`; the email's
structure comes from `task.md`. This file routes listings; `task.md` renders them.

## Fit levels → category

| Fit level | Definition | Goes to |
|---|---|---|
| **Strong fit** | Requirements name Python, Java, SQL, C, or C++ as a core language at a level consistent with coursework or early-professional proficiency (not "expert"/"production-grade"), at an intern/entry level | ranked section for its term, near the top |
| **Worth a stretch** | Requirements name a tool the candidate has only early-stage exposure to (SQL beyond basic querying, Playwright/Selenium in CI, JavaScript, a specific framework) as a primary requirement, otherwise entry-level with no hard blocker | ranked section for its term, below strong fits |
| **Skills gap — close** | the gap is a specific tool/library adjacent to what they know (a particular SQL dialect, a testing framework, a specific Python library) | *Skills gap — close* |
| **Skills gap — out of reach** | a different skill domain with no foundation — embedded/RTL/FPGA, mobile-native (Kotlin/Swift), infrastructure toolchains (Kubernetes/Terraform), production ML frameworks | *Skills gap — out of reach* |

- **C/C++ note:** counts toward strong fit only for general software roles. In an embedded, firmware, RTL, or driver-level listing the domain decides → *Skills gap — out of reach*.
- **No named hard skill** (generic "interest in software", "basic understanding of computer science and data"). Not automatically strong or a gap: rank normally — Strong if the work clearly overlaps the candidate's project background, else Worth a stretch — and say plainly that no specific tool was required.

## Hard blockers → *Hard requirement not met*
- **Stated GPA cutoff above the candidate's GPA** in Requirements — state the number. (A cutoff only under Desired Qualifications is *not* a blocker.)
- **Active security clearance required, or stated eligibility to obtain one.**
- **Work authorization outside the candidate's country** required, with no sponsorship. For cross-border roles this applies only when Requirements explicitly say so; otherwise rank normally in the lowest location tier.
- **Non-CS engineering degree required** (EE, ChemE, aerospace, biomedical, civil).
- **Prior internship experience required** — only as a Requirement, not a Desired Qualification.

**Citizenship is not a blocker when the candidate holds it.** Requirements like
"must be a citizen"/"US person"/export-control are satisfied for a citizen; keep
those listings ranked. Sponsorship/visa language is irrelevant: never flag it,
never mention it, never treat it as a plus.

## Requirements vs Desired Qualifications
Judge against **Requirements only**. Desired/Preferred is non-binding — never
filter or downgrade for something that appears only there. **One exception:** if
`Requirements` is empty, use Desired as a soft basis, rank normally, and note in
the Verify line that no requirements were listed — nothing there can be a hard
blocker.

## Location tiers
Set the tiers from `profile/preferences.md` (the candidate's ranked locations and
home base). A workable default:

- **Tier 1** — the candidate's top-ranked location(s), or fully remote.
- **Tier 2** — their secondary metro / home base.
- **Tier 3** — other major metros.
- **Tier 4** — any other in-country location.
- **Tier 5** — abroad (lowest, for work-authorization friction). Default ranking, not a filter.

Suburbs/metro areas take their metro's tier.

If a city isn't on the list: (1) not in country → step 4; (2) within ~100 mi of
the top metro → Tier 1; (3) within ~100 mi of the home base → Tier 2; (4) else
in-country → Tier 4, abroad → Tier 5, anywhere else → *Location mismatch* if in
person/hybrid. When tiering by proximity, name the reference point and rough
distance in the Verify line.

**Filter to *Location mismatch* only when** the location is outside the
candidate's country/region **and** `Workplace Model` is In Person or Hybrid with
no remote option.
- `More Locations` present → use the best tier and name which location earns it.
- No location at all → *Needs manual check*.
- Note relocation in the Verify line for Tier 3 and below.

## Company competitiveness
- "top-tier CS program", "exceptional academic record", "competitive programming background" → *Hard requirement not met* (even with no numeric GPA).
- **Quant trading / quantitative research** → *Wrong field entirely*, regardless of stated requirements.

## Eligibility and timing
- Graduation: **[GRADUATION DATE]** (from `profile/preferences.md`).
- A listing requiring "currently enrolled full-time" for a term after graduation → *verify*, keep ranked.
- A graduation-date gate later than the candidate's → *verify enrollment*, keep ranked, unless a separate hard blocker already disqualifies it.

## Precedence
**Hard blockers win** — *Hard requirement not met* and enrollment blockers take
precedence over skills-gap, location, or field categories. Pick the most specific
reason and move on.
