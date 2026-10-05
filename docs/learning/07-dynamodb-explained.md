# Amazon DynamoDB — explained

**Owner:** Somitha, with MD · **Read after:** `06-lambda-explained.md` · **Code:** `backend/src/common/keys.py`, `queries.py`

---

## 1. The one idea that matters

**Level 1 — simple.** A filing cabinet where every file has a label, and you fetch files by label. You cannot wander through the drawers looking for something — you must know the label. In exchange, fetching by label is instant no matter how many files there are.

**Level 2 — technical.** DynamoDB is a managed key-value and document store. Items live in partitions chosen by hashing the **partition key**; within a partition they are stored sorted by the **sort key**. A `Query` must supply a partition key, which is why it stays fast as the table grows: it reads one partition, never the table.

**The consequence drives our whole data model:** in SQL you store the data normally and write whatever query you need later. In DynamoDB you decide the questions first and design the keys so each question is one query. Getting this backwards is the classic DynamoDB mistake.

## 2. SQL versus DynamoDB

| | PostgreSQL | DynamoDB |
|---|---|---|
| Find anything | `SELECT ... WHERE anything` | Only by key, or by an index you created for it |
| Joins | Yes | None. Model the access pattern instead |
| Schema | Fixed, enforced | Keys only; other attributes are per-item |
| Scaling | Bigger instance, then replicas | Horizontal, automatic |
| Idle cost | Billed hourly, always | **Nothing** (on-demand) |
| Design order | Data first, queries later | **Queries first, keys second** |

Neither is better. If the campus wanted arbitrary analytical queries, a relational store or an S3 data lake with Athena would be the right answer — and saying that is a stronger exam answer than claiming DynamoDB wins everywhere.

## 3. Our table

```text
Table: campuspulse-dev-events          on-demand · TTL 30d · PITR on

  pk  = DAY#2026-10-04                       ← partition key: one day
  sk  = 2026-10-04T14:05:00Z#evt-0042        ← sort key: time, then id

  GSI1 "by-building"
  gsi1pk = BLD#Library-A#2026-10-04 , gsi1sk = <same as sk>

  GSI2 "alerts"  (sparse!)
  gsi2pk = ALERT#2026-10-04        , gsi2sk = <same as sk>
```

**Why the date is the partition key.** Everything the dashboard asks is about a day: today's events, today's alerts, today's statistics. One day = one partition = one query.

**Why the sort key starts with the timestamp.** Sort keys are stored in order, so "newest first" is `ScanIndexForward=False` plus a `Limit`. No sorting, no over-reading. The `#evt-id` suffix only keeps two events in the same second distinct.

**Why GSI2 is the elegant part.** An item appears in an index only if it *has* that index's key attributes. `cp-ingest` writes `gsi2pk` only when severity is not normal:

```python
if rules.is_alert(severity):
    item["gsi2pk"] = alert_partition(ts)
```

So the alerts index physically contains alerts and nothing else. `GET /alerts` reads a small index rather than reading the whole day and discarding the 95% that are normal. That is a **sparse index**, and it is worth being able to explain — it is the difference between a design and a workaround.

## 4. Query versus Scan

| | Query | Scan |
|---|---|---|
| Reads | One partition | **Every item in the table** |
| Needs | A partition key | Nothing |
| Cost as data grows | Flat | Grows forever |

**There is no `Scan` anywhere in this system**, and a test enforces it (`test_no_builder_can_produce_a_scan`). The read roles are not even granted `dynamodb:Scan` — if someone added one, it would fail with `AccessDenied` rather than quietly working and getting slower every week.

The single exception is exporting the finished table once at cleanup, which is in the cleanup guide and is not part of the running system.

## 5. Our five queries

| Need | Index | Key condition |
|---|---|---|
| Recent events, campus-wide | table | `pk = DAY#<date>` |
| Recent events, one building | GSI1 | `gsi1pk = BLD#<building>#<date>` |
| Today's alerts | GSI2 | `gsi2pk = ALERT#<date>` |
| Everything today, for stats | table | `pk = DAY#<date>` |
| One specific event | table | `pk` + `sk` |

Note the second row: asking for one building **switches index** rather than filtering. A `FilterExpression` runs *after* the read, so you still pay to read everything you then throw away. We use a filter in exactly one place — severity on the alerts index — because that index is already tiny.

## 6. Pagination

A query returns up to 1 MB, then hands back a `LastEvaluatedKey`: where to resume. We base64-encode it as an opaque `next_token` so clients cannot hand-craft one.

`GET /stats` pages through up to ten pages and then stops, setting `truncated: true`. **That ceiling is real and we report it** rather than hide it: a day with tens of thousands of events would be summarised from only its most recent slice.

## 7. TTL — items that delete themselves

Every item carries `expires_at`, 30 days ahead. DynamoDB deletes expired items automatically and does not charge for the deletion. Three benefits: storage stays far inside the 25 GB free allowance, a smaller table restores faster (which improves our RTO), and it is a genuine data-lifecycle decision to discuss in the report.

## 8. The limit of our design, stated before we are asked

All of one day's writes land in **one partition**, and a partition sustains roughly 1,000 write units per second. So this design tops out near a thousand events per second — far beyond our prototype, but a real ceiling.

**The fix, if we needed it:** add a shard suffix — `DAY#2026-10-04#0` … `#9` — spreading writes across ten partitions and reading all ten in parallel. We are not building it. We can describe it, which is what the scalability section is for.

Knowing your design's ceiling and its remedy is worth more marks than claiming there isn't one.

## 9. Verify it yourself

```bash
# Query, not scan: one partition, newest first
aws dynamodb query --table-name campuspulse-dev-events \
  --key-condition-expression "pk = :pk" \
  --expression-attribute-values '{":pk":{"S":"DAY#2026-10-04"}}' \
  --no-scan-index-forward --max-items 5

# The sparse index: count alerts vs count everything
aws dynamodb query --table-name campuspulse-dev-events \
  --index-name gsi2-alerts \
  --key-condition-expression "gsi2pk = :pk" \
  --expression-attribute-values '{":pk":{"S":"ALERT#2026-10-04"}}' \
  --select COUNT
```

Compare the two counts. The gap is the work the sparse index saves on every single dashboard refresh.

---

## Can you explain this?

1. Why must every DynamoDB query supply a partition key?
2. What makes GSI2 "sparse", and what does that buy us?
3. Why is "newest first" free in our design?
4. Why does filtering by building switch index instead of using a filter?
5. What is the known limit of our key design, and how would you fix it?

### Answers

1. Because the partition key is hashed to locate the partition the items live in. That is what makes a query read one partition instead of the table, and why it stays fast as data grows.
2. `cp-ingest` writes the `gsi2pk` attribute only for abnormal events, and an item enters an index only if it has that index's keys. So the index contains alerts and nothing else, and `GET /alerts` reads a small index instead of reading the day and discarding the normal 95%.
3. The sort key begins with the timestamp and sort keys are stored in order, so reading the partition backwards with a limit returns the newest items — no sorting and no over-reading.
4. A `FilterExpression` is applied after the read, so you pay to read everything and then discard most of it. GSI1 is keyed by building, so the same question becomes one targeted query.
5. One day's writes all land in one partition, which sustains roughly 1,000 writes per second. The fix is a shard suffix on the partition key — `DAY#<date>#0..9` — spreading writes over ten partitions and querying all ten in parallel.
