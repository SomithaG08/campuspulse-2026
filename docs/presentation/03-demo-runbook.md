# Live Demo Runbook

**Four minutes. Six steps. One person drives — Madhavan.**

The demo is the single highest-risk part of the presentation and the single most convincing. Everything below exists to make it boring.

---

## Thirty minutes before

```bash
bash scripts/smoke-test.sh
```

Six checks in fifteen seconds. It also **pays the cold start**, so the first request the examiner sees is warm — a first call takes 1-3 seconds, and that looks like a slow system when it is just a cold container.

**If the smoke test fails, do not start the demo. Play the video.** That decision is made now, calmly, not on stage.

## Ten minutes before

- Two windows only: terminal and browser. Close everything else — chat, email, notifications.
- Terminal font large enough to read from the back row.
- Browser already on the dashboard, signed in as `ops`.
- A second browser profile or private window, ready for the `staff` login.
- The backup video open in a third tab, minimised.
- `--force-alert` command typed but **not pressed**.

## The sequence

### 1 — The dashboard (30 s)

Already open, with data from an earlier run. Five tiles, alerts, occupancy, energy, recent events.

> *"This is what the operations team sees."*

### 2 — Start the simulator (45 s)

```bash
python simulator/simulator.py --interval 2 -n 20
```

Events scroll in the terminal; numbers move on the dashboard within ten seconds.

> *"Each line is a sensor reading. The severity shown is the server's decision, not the device's."*

### 3 — Force an alert (45 s) — **the moment that matters**

```bash
python simulator/simulator.py --force-alert -n 1
```

The terminal prints a critical line with its reason. Within ten seconds a red row appears on the dashboard.

> *"Fifty-eight people in a room that holds forty-five. The device reported this as normal. The server overruled it."*

Pause here. Let them read it.

### 4 — Trace it (45 s)

```bash
aws dynamodb query --table-name campuspulse-dev-events \
  --key-condition-expression "pk = :pk" \
  --expression-attribute-values '{":pk":{"S":"DAY#'$(date -u +%Y-%m-%d)'"}}' \
  --no-scan-index-forward --max-items 1
```

Then the log line for the same `request_id`.

> *"The same event: in the response, in the database, in the log. One identifier ties all three."*

### 5 — The two roles (45 s) — **the security proof**

Sign in as `staff@northbridge.edu` in the second window. **The alerts panel is gone.**

```bash
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $STAFF_TOKEN" $API/alerts
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $STAFF_TOKEN" $API/events
```

> *"403, then 200. Same user, same token, different route. Hiding the panel is a convenience — the 403 is the control."*

### 6 — Monitoring (30 s)

The CloudWatch dashboard, with the curves from the last three minutes.

> *"And this is the same system, from the operator's side."*

---

## If something fails

| What fails | Do this |
|---|---|
| Dashboard does not update | Press Refresh once. Still nothing → go to curl, the API is what matters |
| Simulator cannot connect | Say the Wi-Fi is refusing and switch to the video. Do not debug on stage |
| Login fails | Switch to the video |
| Anything takes more than 10 seconds | Keep talking, then move on. Silence is what the audience remembers |
| Total failure | *"The network is not cooperating — here is the recording we made yesterday."* Play it. **This is a prepared outcome, not a disaster** |

**The rule: one attempt, then the video.** Never debug in front of an examiner. A smooth fallback reads as preparation; a live debugging session reads as an unfinished project.

## The backup video

**Record it the day before**, not the morning of.

- Screen recording, 3-4 minutes, exactly the sequence above
- Your voice over it, or clean captions
- Stored **locally on at least two laptops** — not only in the cloud, because the failure case is the network
- Checked: does it actually play, with sound, on the presentation machine?

The brief (§13) accepts a video as demo evidence. This is not a consolation prize; it is the required insurance.

## After the demo

Say the sentence that closes the loop:

> *"So: an event entered the system, was judged critical by rules we wrote, was stored, appeared on the dashboard, and is traceable in the logs. And the same page shows a different thing to a different role."*

Then go to slide 16.
