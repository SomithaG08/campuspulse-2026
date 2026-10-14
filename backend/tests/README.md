# Tests

```bash
cd backend && python -m pytest tests -q
```

No AWS account, no network, no credentials — these test the pure logic in `common/`, which is why they run in under a second.

| File | Covers | Count |
|---|---|---|
| `test_validation.py` | Accepting good events, rejecting every category of bad one | 30 |
| `test_rules.py` | Both sides of every severity threshold in the data model | 37 |
| `test_keys.py` | Key construction, ordering, TTL, the sparse alerts index | 7 |
| `test_queries.py` | All five access patterns, parameter parsing, pagination tokens, and the guarantee that no builder can produce a `Scan` | 24 |
| `test_aggregate.py` | Every field of the `/stats` response, Decimal handling, newest-first occupancy | 15 |

**113 passing as of Phase 6.** Handler and API tests, which need a deployed stack, come in Phase 11.
