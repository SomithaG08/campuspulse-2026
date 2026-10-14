# The simulator — explained

**Owner:** Madhavan · **Read after:** `05-api-explained.md` · **Code:** `simulator/simulator.py`

---

## 1. What it is and why it exists

We have no sensors bolted to the walls of a real university, so this program pretends to be them. It invents plausible readings for rooms that actually exist in our campus configuration, signs in like any other client, and POSTs each reading to the API.

The brief asks for "simulated campus data generation" (§7), and this is it. **Nothing in the backend knows the events are synthetic** — the same code path would serve real hardware. That is a design property worth stating at the oral: we simulated the *devices*, not the *system*.

## 2. The one thing to understand first

```python
sys.path.insert(0, ... / "backend" / "src")
from common import campus_config as cfg
from common import rules
```

The simulator **imports the backend's own configuration and rules** instead of keeping its own copy.

Why this matters: if the simulator believed room A203 held 60 people and the backend believed 45, every alert would be wrong and neither side would look at fault. One file, imported by both, makes that disagreement impossible. This is the mitigation for the integration risk that breaks most four-person projects — and it is two import lines, not a process.

## 3. Running it

```bash
export CAMPUSPULSE_API=https://xxxx.execute-api.eu-west-3.amazonaws.com
export CAMPUSPULSE_USER=device@campuspulse.local
export CAMPUSPULSE_PASSWORD='...'

python simulator.py --dry-run -n 10      # print 10, send nothing, no AWS, no cost
python simulator.py -n 100               # send 100 and stop
python simulator.py --interval 5         # one every 5 seconds until Ctrl-C
python simulator.py --force-alert -n 3   # three guaranteed critical events
```

**Credentials come from environment variables, never from the command line.** A password typed as an argument lands in your shell history and in the process list where other users can see it.

**Start with `--dry-run`.** It prints each event *and* the severity the server would assign — computed with the very same `rules.py` the backend uses. It costs nothing and it is how you check your changes before spending a single request.

## 4. What it generates

| Type | Weight | Normal | When abnormal |
|---|---|---|---|
| `occupancy` | 35 % | capacity × a time-of-day factor | 105–145 % of capacity |
| `temperature` | 30 % | 19–25 °C | 10–17.5 or 26.5–34 °C |
| `humidity` | 15 % | 33–57 % | 12–29 or 61–85 % |
| `energy` | 12 % | baseline × 0.2–1.05 | baseline × 1.55–2.4 |
| `equipment` | 5 % | 0 (operational) | 1 degraded or 2 failed |
| `service_request` | 3 % | priority 1–2 | priority 3 (urgent) |

Weights are deliberately uneven: a real campus mostly measures occupancy and temperature, and equipment failures are rare — which is exactly what makes them worth alerting on.

## 5. The time-of-day curve

```text
occupancy as a fraction of room capacity

 1.0 │          ████              ████
     │          ████     ██       ████
 0.5 │     ██   ████   ██████     ████
     │     ██   ████   ██████   ██ ████ ██
 0.0 │ ─── ██ ─ ████ ─ ██████ ─ ██ ████ ██ ───
       0-7  7-9  9-12  12-14   14-18 18-22  22+
            fill  peak  lunch   peak  empty
```

It would have been easier to pick a random number. But a dashboard showing pure noise looks like a toy, and one showing a plausible daily rhythm looks like a system. The professor will be looking at that dashboard.

## 6. `--force-alert`, and why it exists

During the demo you need an alert to appear **on cue**. `--force-alert` makes every event abnormal, and specifically *critical* — not merely a warning.

That distinction came out of a test. The anomalous occupancy range was 105–145 % of capacity, which straddles the 120 % critical line, so a forced alert sometimes produced only a warning. A demo alert that sometimes lands as something milder is a demo that sometimes does not land. Forced events now use ranges comfortably past the critical threshold, and `test_forced_alerts_are_always_critical` checks 300 of them.

## 7. The cost guard rails

The brief warns about runaway spend, and a simulator is the obvious way a student project burns its credits in an afternoon. So the CLI refuses:

| Refused | Why |
|---|---|
| `--interval` below 0.5 s | A tight loop against a pay-per-request API |
| `-n` above 10,000 | No accidental extra zero |
| `--anomaly-rate` outside 0–1 | Nonsense input |
| No API URL unless `--dry-run` | So you cannot accidentally hit the wrong endpoint |

Each refusal has a test. Guard rails that nobody verifies are decoration.

## 8. The token

The simulator calls `POST /login` once, keeps the token, and **refreshes it five minutes before it expires**. Tokens last an hour; a long run would otherwise start returning 401 partway through, which is a confusing failure to debug live.

Note that the simulator authenticates as `device@campuspulse.local`, an ordinary Cognito user in the `ops` group — not a machine-to-machine client. Cognito's M2M token requests have **no free tier** and are billed per request, so an ordinary user is both free and a better demonstration: the device goes through exactly the same authentication a human does.

## 9. Zero dependencies, on purpose

`simulator/requirements.txt` is empty. The HTTP code uses `urllib` from the standard library rather than `requests`.

`requests` would be a few lines shorter and nicer to read. But "no pip install" means four teammates on four laptops can run this immediately, and nothing can fail on demo day because a dependency would not install. **For a tool whose entire purpose is to work during a live demonstration, reliability beats elegance** — and being able to explain that choice is better than having made the prettier one.

## 10. Reading the output

```text
  !! 2026-10-04T14:05:00Z  Library-A/A203    occupancy=58 people    critical
        -> occupancy 58 exceeds 120% of capacity 45
  !  2026-10-04T14:05:05Z  Arts-C/C005       temperature=17.3 celsius  warning
        -> temperature 17.3 celsius is outside the normal range 18 to 26
     2026-10-04T14:05:10Z  Admin-E/E100      occupancy=6 people     normal
```

`!!` critical, `!` warning, blank normal. **The severity shown is the server's answer, not the simulator's** — in a real run it is read from the API response. The simulator sends `"severity": "normal"` on every event and the server overrules it, which is the integrity control from the threat model, visible in the terminal.

## 11. Testing it

```bash
python -m pytest simulator/tests -q
```

The test that matters most feeds **1000 generated events through the backend's real validator**. If the simulator could ever produce something the API rejects, it fails here rather than during the presentation.

---

## Can you explain this?

1. Why does the simulator import `campus_config.py` from the backend instead of defining the campus itself?
2. Why does the output show a severity the simulator did not choose?
3. What does `--force-alert` do, and why does it guarantee *critical* rather than any alert?
4. Why are there no dependencies in `requirements.txt`?
5. Name two cost guard rails in the CLI and what each prevents.

### Answers

1. So the simulator and the server can never disagree about room capacities, energy baselines or thresholds. Two copies of that configuration would drift and every alert would become unexplainable.
2. Because the server decides severity, not the device. The simulator sends `"severity": "normal"` on every event and the API recomputes it from the value and the room's capacity — so a sensor cannot declare itself normal and hide a problem.
3. It makes every event abnormal for the live demo. It guarantees critical because the ordinary anomalous ranges straddle the critical threshold, so a forced alert could otherwise come out as a mere warning — and a demo alert that sometimes lands as something milder is unreliable.
4. It uses only the standard library, so any teammate can run it with no install step and nothing can break on demo day because a package would not install.
5. `--interval` below 0.5 s is refused (a tight loop against a pay-per-request API), and `-n` above 10,000 is refused (an accidental extra zero). Also: no API URL unless `--dry-run`, so you cannot accidentally hit the wrong endpoint.
