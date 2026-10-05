# Phase 14 — Academic Report (complete, pending your review)

## What we built

`docs/report/implementation-report.md` — all eleven sections the brief requires, plus the contribution table and references. About 5,900 words before screenshots.

## Files created

| File | What it is |
|---|---|
| `docs/report/implementation-report.md` | The report |
| `docs/report/README.md` | What to fill in before submitting, and how to export to PDF |

## How it was assembled

Entirely from material this project actually produced — the phase summaries, the architecture decisions, the threat model, the cost model, the test results. Nothing was written from imagination, and **51 placeholders** mark everything that must come from a real run.

## What the report does that most student reports do not

**It states its own limits.** Single-region with no failover; threshold detection with no adaptive model; a throughput ceiling of roughly 1,000 writes/second with the specific fix named; tokens that cannot be revoked before expiry; a broad deployment identity. Each appears in the section where it belongs, rather than waiting to be discovered by a question.

**It distinguishes claims from measurements.** RTO is left as a blank until the restore is rehearsed. Two alarm thresholds are described as initial estimates. Several cost figures are marked unverified with the script that resolves them. A number nobody has observed is never written down.

**§4.3 is real.** Five genuine issues with their causes and fixes: the unreliable `--force-alert`, the test assumption that turned out to be wrong, the CSS bug that only a rendered page could reveal, the nine documentation inconsistencies a script found, and the pricing pages that could not be read programmatically. Most reports have an empty or invented "challenges" section; this one has the actual history.

**It is honest about AI assistance** in the references, in terms the integrity requirement (§16) asks for.

## Testing

| Check | Status |
|---|---|
| All eleven required sections present, in the brief's order | **Executed — verified against §10** |
| Every quoted figure traceable to a verified source or marked as a placeholder | **Executed** |
| 51 placeholders, each marking something that needs a real run | **Executed — counted** |
| 131 unit tests | **Executed — still passing** |
| Report exported as PDF | **Not executed** — needs the screenshots first |

## Problems / open items

| Item | Who |
|---|---|
| **51 placeholders** to fill from real runs — search `[INSERT` and `[MEASURED` | everyone |
| **§11.6 "What the team learned"** — each member writes their own two or three sentences. Nobody can write this for you | everyone |
| §12 contribution table — from what happened, not from the plan | everyone |
| Export to PDF once the screenshots are in | whoever owns the report |
| **Still open:** the AWS account's plan and creation date (risk C5) | You |

## Next phase

**Phase 15 — Presentation and demo.** Fifteen slides with speaker notes, a per-member speaking split, the live demo sequence, the backup plan for when the venue Wi-Fi fails, and the anticipated questions with answers.

Then **Phase 16** — the final requirement audit, which maps every line of the brief to evidence and states plainly what is Complete, Partial, Not implemented or Not verified.
