# CloudWatch and observability — explained

**Owner:** MD · **Read after:** `06-lambda-explained.md` · **Code:** `infrastructure/terraform/alarms.tf`, `backend/src/common/log.py`

---

## 1. Three words that are not the same thing

| | What it is | Answers | Ours |
|---|---|---|---|
| **Log** | A line of text recording that something happened | *What happened to this one request?* | One JSON line per event stored |
| **Metric** | A number over time | *How is the system doing overall?* | `EventsIngested`, `AlertsRaised` |
| **Alarm** | A rule watching a metric, with a state | *Should someone look right now?* | Four of them |

The progression matters: **logs** tell you about one request, **metrics** tell you about all of them, **alarms** tell you when to care. A system with logs and no metrics means trawling text to answer "is it busy?". Metrics with no alarms means someone has to be watching.

## 2. Monitoring vs observability

**Monitoring** is watching signals you decided to watch in advance. **Observability** is being able to answer questions you did not anticipate, from what the system already emits.

That is why our logs are **structured JSON** rather than sentences:

```json
{"level":"INFO","request_id":"a1b2c3","event_id":"evt-42","building":"Library-A",
 "room":"A203","severity":"critical","latency_ms":41}
```

`print("stored event")` is unsearchable. The line above can be queried:

```sql
fields @timestamp, building, room, severity
| filter severity = "critical"
| stats count() by building
```

Same effort to write, a completely different amount of use. That query was never planned for — which is the point.

## 3. EMF: metrics for free

The obvious way to publish a metric is `PutMetricData` — an extra API call, extra latency, billed per request.

We use **Embedded Metric Format** instead: CloudWatch extracts metrics from a specially shaped log line. So `log.metric("EventsIngested", 1, Severity="critical")` prints one line, and the log we were writing anyway *becomes* the metric. No extra call, no extra cost.

**The dimension discipline:** every distinct combination of dimension values is a separate custom metric, and the free tier allows ten. Splitting by building would be five metrics per counter; by room, eleven. We split by severity only — three metrics total, comfortably inside the allowance. That is a cost decision hiding inside a monitoring decision.

## 4. Our four alarms

| Alarm | Watches | Fires when | What it means |
|---|---|---|---|
| `ingest-errors` | Lambda `Errors` | ≥ 1 in 5 min | **Broken.** At our volume any error deserves a look |
| `api-5xx` | API Gateway `5xx` | ≥ 1 in 5 min | The front door is failing |
| `alert-burst` | `AlertsRaised` | ≥ 20 in 5 min | **The campus** is having a bad day — or someone left `--force-alert` running |
| `invocation-ceiling` | Lambda `Invocations` | ≥ 2000 in 5 min | **The budget** is under attack. A runaway loop |

Three watch the infrastructure; one watches the campus. The last one is a **cost control**, not a performance control — it catches a spend problem days before the bill would.

**Two of these thresholds are guesses, and the code says so.** A threshold invented before a system has ever run is exactly that. They are variables, and the report will record both the initial guess and the tuned value — which is a better story than a number that was always mysteriously right.

### One subtlety: `treat_missing_data`

A period with no traffic would otherwise leave an alarm at `INSUFFICIENT_DATA`, sitting grey. We set `notBreaching` — no traffic is not a failure. Without it, a dashboard full of grey alarms teaches everyone to ignore alarms, which is worse than having none.

## 5. The dashboard

Six widgets, arranged so the **top row answers "is it working?"** and the **bottom row answers "what is it doing?"**:

```text
┌─────────────────────────┬─────────────────────────┐
│ Requests and errors     │ Latency (p95)           │
├─────────────────────────┼─────────────────────────┤
│ Campus events & alerts  │ API responses by class  │
├─────────────────────────┼─────────────────────────┤
│ DynamoDB capacity       │ Recent errors (log)     │
└─────────────────────────┴─────────────────────────┘
```

**Why p95 and not average.** An average hides the slow requests: if 95 are fast and 5 are terrible, the mean looks fine and five users are unhappy. p95 says "95 % of requests were at least this fast", which is what someone actually experiences. Expect our p95 to show cold starts.

This is **not** the CampusPulse dashboard. Two different dashboards, two different audiences: CloudWatch is for us and is about the *system*; CampusPulse is for the operations team and is about the *campus*. Do not mix them up on a slide.

## 6. Costs, verified

| Thing | Free allowance | We use |
|---|---|---|
| Log ingestion + storage + Insights | 5 GB combined | « 1 GB, retention 7 days |
| Custom metrics | 10 | 3 |
| Alarms | 10 | 4 |
| Dashboards | 3 | 1 |

**Retention is set explicitly to 7 days in Terraform.** The default is "never expire", which quietly accumulates storage cost forever. We also create the log groups ourselves rather than letting Lambda create them, precisely so that default never applies.

## 7. Prove it works — evidence for the report

```bash
# 1. a specific request, end to end
aws logs filter-log-events --log-group-name /aws/lambda/campuspulse-dev-ingest \
  --filter-pattern '"<request_id>"'

# 2. the metric exists
aws cloudwatch get-metric-statistics --namespace CampusPulse \
  --metric-name EventsIngested --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) --period 300 --statistics Sum

# 3. drive an alarm into ALARM on purpose - this is the screenshot that counts
python simulator.py --force-alert --interval 0.5 -n 30
aws cloudwatch describe-alarms --alarm-names campuspulse-dev-alert-burst \
  --query 'MetricAlarms[].{Name:AlarmName,State:StateValue,Reason:StateReason}'
```

**Step 3 is the one the report needs.** An alarm that has never fired is an untested alarm, and "we configured alarms" is a much weaker sentence than "we triggered one deliberately, here is the screenshot, here is how long it took to fire".

---

## Can you explain this?

1. What is the difference between a log, a metric and an alarm?
2. Why are our logs JSON instead of plain sentences?
3. What is EMF and what does it save us?
4. Why does the latency widget show p95 rather than the average?
5. Which of our alarms is about cost rather than correctness?

### Answers

1. A log records what happened to one request; a metric is a number over time across all of them; an alarm is a rule that watches a metric and changes state so somebody knows to look.
2. Because structured fields can be queried — "count critical events by building" is one Logs Insights query against lines we were already writing. Sentences can only be read.
3. Embedded Metric Format: CloudWatch extracts metrics from a specially shaped log line, so we publish metrics without `PutMetricData` calls — no extra latency and no per-call charge.
4. An average hides the slow tail. If 95 requests are fast and 5 are terrible, the mean still looks fine. p95 reflects what a real user experiences, including our cold starts.
5. `invocation-ceiling`. Far more invocations than a demo produces means a runaway client, and on a pay-per-request API that is a spend problem — visible here days before it would show on a bill.
