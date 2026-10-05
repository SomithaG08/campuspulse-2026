# Testing

| File | What it is |
|---|---|
| `01-test-plan.md` | What we test, at which layer, with the honest status of each group |
| `../../tests/api/run_api_tests.py` | 45 API checks against a deployed stack; writes the evidence JSON |
| `../evidence/api-test-results.json` | **Placeholder** until a real run overwrites it |

```bash
python -m pytest backend/tests simulator/tests -q   # 131, no AWS needed
python tests/api/run_api_tests.py                   # needs a deployment
```

Explanation for beginners: `docs/learning/17-testing-explained.md`
