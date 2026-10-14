# Report

`implementation-report.md` — all eleven sections the brief requires (§10), plus contributions (§16) and references.

## Before submitting

1. **Fill every `[INSERT …]` and `[MEASURED: ___]`** from real runs. There are 51. Search for `[INSERT` and `[MEASURED`.
2. **Delete the editorial note** at the top.
3. **§11.6 must be written by each member individually.** It is the one section nobody can write for you, and an examiner can tell.
4. **§12 contributions** — fill from what actually happened, not from the plan.
5. Re-read §7 and §10: any figure still marked `unverified` or any status still `[STATUS: …]` must be resolved or honestly stated.

## Export to PDF (§10 requires PDF)

```bash
pandoc docs/report/implementation-report.md -o docs/report/CampusPulse-2026-Report.pdf \
  --toc --number-sections -V geometry:margin=2.5cm -V fontsize=11pt
```

No pandoc? Paste into Google Docs or Word, apply heading styles, insert the screenshots where the placeholders are, and export. Either way, **the screenshots must be inserted** — the placeholders are not acceptable in the submitted PDF.

## Word count

~5,900 words before screenshots. Dense rather than padded: every claim is traceable to a file in the repository or marked as not yet verified.
