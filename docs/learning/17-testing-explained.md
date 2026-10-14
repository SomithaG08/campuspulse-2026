# Testing — explained

**Owner:** Madhavan · **Code:** `backend/tests/`, `simulator/tests/`, `tests/api/`

---

## 1. Why bother

Not to prove the code works — you cannot prove that. To find out **quickly** when it stops working.

Concretely: the severity thresholds live in one file, imported by the backend and the simulator. If someone edits `critical_above` from 1.2 to 1.5 to make a demo calmer, 37 tests go red in under a second. Without them, you find out at the oral exam when the alert does not fire.

## 2. Two layers, and why both

```text
   API tests  (45)   ──  does the DEPLOYED SYSTEM behave?   needs AWS
   Unit tests (131)  ──  is the LOGIC right?                needs nothing
```

A system can pass every unit test and still return 500 because an IAM policy is wrong. It can be flawlessly deployed and still classify a critical event as normal. **Neither layer substitutes for the other**, and knowing why is a likely exam question.

## 3. Why the unit tests need no AWS

Because the interesting logic imports no `boto3` and touches no network:

```text
common/validation.py  common/rules.py  common/keys.py       ← pure, testable
common/queries.py     common/aggregate.py

handlers/ingest.py    handlers/query.py   handlers/stats.py ← thin, AWS-facing
```

That split is deliberate. **Code that can only be tested by deploying it does not get tested** — the loop is too slow, so people skip it. 131 tests in one second gets run after every change.

## 4. Anatomy of a test

```python
def test_worked_example_matches_the_documentation():
    """This exact sentence appears in 04-data-model.md and 06-data-flow.md."""
    severity, reason = classify(event(value=58))
    assert severity == CRITICAL
    assert reason == "occupancy 58 exceeds 120% of capacity 45"
```

Three things to notice. The **name says what should be true**, so a failure is readable without opening the file. The **docstring says why it exists** — this one pins the documentation and the code together, so they cannot drift apart silently. And it checks **the message, not just the severity**, because the reason string is part of the product.

## 5. Test the boundaries, not the middle

```python
@pytest.mark.parametrize("value,expected", [
    (45, NORMAL),     # exactly at capacity is not yet over
    (46, WARNING),    # just over 100%
    (54, WARNING),    # 120% exactly - not yet critical
    (55, CRITICAL),   # just over 120%
])
```

Nobody writes `if value > capacity` wrongly for 10 and rightly for 58. The bugs live at 45 and 46, at 54 and 55. **A threshold without a test on each side of it is an untested threshold.**

## 6. Two tests that are really design guarantees

```python
def test_no_builder_can_produce_a_scan():
def test_generated_events_always_pass_server_validation():
```

The first enforces an architectural rule: every access pattern supplies a partition key, so no code path can degrade into a full-table `Scan`. The second runs 1000 generated events through the backend's real validator, so the simulator can never be the reason a live demo shows an error.

Ordinary tests check a function. These check a **property of the whole system**, and they are the ones to mention at the oral.

## 7. Most tests should be about failure

`test_validation.py` has 30 tests and most of them assert a **rejection**. That is right: a validator only ever tested with good input is not tested at all. The valuable cases are `"42"` as a string, `True` (which is an `int` in Python, so it would pass a naive numeric check), a 4000 °C reading, and a timestamp three days old.

## 8. The honest status words

Every test in the report is labelled **Executed**, **Created not executed**, or **Not created**. No exceptions, no softening.

Right now: unit tests **Executed, 131 passed**. API tests **Executed against the live deployment on 5 October 2026, 45 passed** (`docs/evidence/api-test-results.json`).

They *were* run once against a throwaway local stand-in built on the project's real logic modules, and all 45 passed. That proves the **test suite is correct**; it proves **nothing about AWS**. Both halves of that sentence belong in the report, because a claim with its limits stated is believed, and a claim without them invites the examiner to find the limits for you.

## 9. Running them

```bash
python -m pytest backend/tests simulator/tests -q     # 131, about a second
python -m pytest backend/tests -q -k "threshold"      # just one topic
python -m pytest backend/tests/test_rules.py -v       # see each name
python tests/api/run_api_tests.py                     # needs a deployment
```

**Run the unit tests before every commit.** They take one second, which is less time than explaining a regression to three teammates.

---

## Can you explain this?

1. Why do we have both unit tests and API tests?
2. Why can 131 tests run without an AWS account?
3. Why do the threshold tests use 45, 46, 54 and 55 rather than 10 and 100?
4. What do `test_no_builder_can_produce_a_scan` and `test_generated_events_always_pass_server_validation` protect?
5. Have the API tests ever passed? Answer precisely.

### Answers

1. Unit tests check the logic, API tests check the deployment. A system can pass every unit test and still 500 on a wrong IAM policy, and it can deploy perfectly while misclassifying events.
2. Because validation, rules, key building, queries and aggregation import no boto3 and touch no network. The AWS-facing handlers are kept thin on purpose, so the interesting logic stays testable on a laptop.
3. Because that is where the bugs are. Nobody gets 10 wrong; people get "greater than" versus "greater than or equal" wrong exactly at the boundary.
4. The first enforces that no query can degrade into a full-table `Scan`. The second guarantees the simulator can never produce an event the API rejects — so it can never be the reason a live demo errors.
5. Yes. First against a local stand-in (which proved the suite itself is correct), then against the live AWS deployment on 5 October 2026: 45 passed, 0 failed. Only the live run says anything about IAM, Cognito, API Gateway and DynamoDB.
