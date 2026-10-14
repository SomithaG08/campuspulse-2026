# Phase 15 — Presentation and Demo (complete, pending your review)

## What we built

Four documents: the slide content, the spoken script, the demo runbook and the anticipated questions.

## Files created

| File | What it is |
|---|---|
| `docs/presentation/01-slides.md` | 17 slides — title, bullets and the visual for each, timed across four speakers |
| `docs/presentation/02-speaking-script.md` | The words to be spoken, and nothing else. ~14 minutes read aloud |
| `docs/presentation/03-demo-runbook.md` | Six steps in four minutes, the pre-flight, and the failure plan |
| `docs/presentation/04-questions.md` | ~25 anticipated questions with answers, including the three hardest |

## How it is structured

**Four speakers, roughly equal time**: Somitha (problem, architecture, data flow, close), Meha (security), MD (dashboard, monitoring, cost), Madhavan (scalability, testing, demo). The brief requires every member to participate and to be able to explain the architecture and the implementation — this split gives each person a section they built themselves.

**The slide rule: at most six bullets, at most eight words.** A slide you read aloud is a slide the audience reads instead of listening to you.

## Three things worth noting

**The demo is engineered to be boring.** One person drives, the smoke test runs thirty minutes beforehand and pays the cold start so the first request the examiner sees is warm, and the failure rule is decided in advance: **one attempt, then the video.** Debugging in front of an examiner reads as an unfinished project; a smooth fallback reads as preparation.

**The demo's centrepiece is the severity override.** Fifty-eight people in a room that holds forty-five, reported by the device as normal, overruled by the server. It is the clearest single idea in the project and it takes fifteen seconds to show.

**The Q&A document rehearses saying "no".** *"That is right — it is designed and documented, and we did not build it"* is a better answer than an invention, and our documentation is already written in those terms. It also prepares the unprompted caveat about the broad deployment identity, because volunteering a limitation is far stronger than being caught by it.

## Testing

| Check | Status |
|---|---|
| Every slide maps to a brief requirement (§11) | **Executed — all seven required topics covered** |
| Script read-aloud length | **Estimated ~14 min** — **must be timed by the team** |
| Demo steps match the real commands in the deployment docs | **Executed — cross-checked** |
| Rehearsed by the team | **Not executed** |
| Backup video | **Not recorded** |

## Problems / open items

| Item | Who |
|---|---|
| **Build the actual slide file** from `01-slides.md` in whatever tool you use | everyone |
| **Time a full rehearsal.** The estimate is not a measurement | everyone |
| **Record the backup video the day before**, store it on two laptops locally | Madhavan |
| Rehearse the Q&A cold — teammate asks, you answer without notes | everyone |
| `[INSERT]` on slide 12 — the actual cost figure | MD |
| **Still open:** the AWS account's plan and creation date (risk C5) | You |

## Next phase

**Phase 16 — Final requirement audit.** Every requirement in the brief mapped to its evidence, with a status of Complete, Partial, Not implemented or Not verified — and a list of what genuinely still needs a human.
