# Big Data and analytics — explained

**Owner:** Somitha · **Read after:** `07-dynamodb-explained.md`

> This module is called **Big Data & Cloud Computing**, so the question *"where is the big data?"* is certain to be asked. This page is how to answer it without overclaiming.

---

## 1. What Big Data means

Data that is too large, too fast or too varied for one machine and ordinary tools. The classic three Vs:

| V | Means | Ours |
|---|---|---|
| **Volume** | how much there is | thousands of events — **small** |
| **Velocity** | how fast it arrives | continuous, one every few seconds — **the right shape, small scale** |
| **Variety** | how many forms it takes | six event types, one schema — **modest** |

Two more often added: **Veracity** (can you trust it? — our validation layer) and **Value** (does it produce a decision? — our alerts).

## 2. The honest answer

**Our prototype is not big data by volume.** A campus of eleven rooms producing a few thousand events fits comfortably in a spreadsheet, and saying otherwise to an examiner is the fastest way to lose credibility.

**What it is: a system built the way big-data systems are built.** Five properties, each a deliberate choice:

| Property | Ours | The alternative we rejected |
|---|---|---|
| **Streaming ingestion** | events processed as they arrive | a nightly batch job |
| **Processing at write time** | severity decided on arrival | classifying later, in a report |
| **Storage designed for access patterns** | partition key chosen from the questions | a relational schema queried ad hoc |
| **Horizontal scaling** | Lambda and DynamoDB add capacity per request | a bigger machine |
| **Schema-on-write validation** | every event checked at the boundary | garbage in, cleaned later |

If the campus grew a thousand-fold, the **architecture** would hold. The *implementation* would need two specific changes, named in §5 — and knowing exactly which two is the difference between a claim and an understanding.

## 3. Where each Big Data idea actually appears in our code

| Concept | Where | What it does |
|---|---|---|
| **Ingestion** | `handlers/ingest.py` | the single entry point for all data |
| **Validation** | `common/validation.py` | rejects malformed and implausible records at the boundary |
| **Stream processing** | `common/rules.py` | classifies each event as it arrives, not in a later pass |
| **Filtering** | GSI2, the sparse index | separates the 5% that matter from the 95% that do not, **at write time** |
| **Aggregation** | `common/aggregate.py` | counts, averages and per-building totals in one pass |
| **Anomaly detection** | `common/rules.py` | threshold rules against capacity and baselines |
| **Partitioning** | `pk = DAY#<date>` | the single most important scaling decision in the system |
| **Data lifecycle** | TTL, 30 days | bounded storage without a cleanup job |

**The sparse index is the clearest big-data idea in the project.** Rather than storing everything and filtering at read time — paying to read 95% of records you throw away, on every single query — the filtering happens once, on write. That is the same instinct behind partitioning, pre-aggregation and materialised views in any large system.

## 4. Anomaly detection without machine learning

Our detection is threshold rules: occupancy against room capacity, temperature against a comfort band, energy against a per-building baseline.

**Why not ML?** Three reasons, and they are the right ones:

1. **Explainability.** Our alert says *"occupancy 58 exceeds 120% of capacity 45"*. A model says *"anomaly score 0.87"*. A campus engineer can act on the first.
2. **Data.** Supervised anomaly detection needs labelled history. We have none — we would be inventing both the data and the labels.
3. **Defensibility.** Every team member can explain a threshold. ML in a student project is usually a library call nobody can defend under questioning.

**What we would do with real history:** a rolling mean and standard deviation per room, flagging values beyond k·σ — so a lecture hall that normally sits at 40% is flagged at 70% even though it is under capacity. That is roughly fifteen lines, it is in the scope document as an optional feature, and it is honest to describe as *not built*.

## 5. What would change at 1000× volume

The question behind the question. Our design's real ceiling, and the fix:

**Ceiling 1 — the hot partition.** All of one day's writes land in `DAY#<date>`, and a DynamoDB partition sustains roughly 1,000 writes per second. At ~1,000 events/second we hit it.

→ **Fix:** shard the partition key — `DAY#2026-10-05#0` … `#9` — spreading writes over ten partitions, querying all ten in parallel and merging. A change to `keys.py` and `queries.py`; the rest of the system does not notice.

**Ceiling 2 — read-time aggregation.** `/stats` reads a day's items and summarises them. At a million events a day that becomes slow and expensive.

→ **Fix:** maintain counters on write. A DynamoDB Stream triggers a Lambda that increments per-hour, per-building aggregate items, so `/stats` reads a handful of pre-computed rows instead of a day of raw events. Classic lambda-architecture shape: raw events for detail, aggregates for speed.

**Beyond that** — tens of millions of events a day — the shape changes: Kinesis or MSK for ingestion, S3 as a data lake in Parquet, Athena or Spark for analytics, DynamoDB kept only for the live operational view.

**We built none of this, deliberately.** Each layer would be machinery nobody on the team could explain, for volume we do not have.

## 6. Why this is still a Big Data project

Because the module teaches how to build systems that handle data at scale, and the assessable skills are:

- choosing a storage model from access patterns rather than convenience
- processing a continuous stream rather than batching
- designing for horizontal scaling
- controlling cost as volume grows
- knowing where your design breaks and what you would change

**We demonstrate all five, at a scale we can actually run, deploy, test and defend.** A prototype that genuinely processed terabytes would cost more than the 100 credits allow and teach less, because nobody on the team could explain all of it.

That is the answer: *not big data by volume; built on big-data principles; and here is precisely what we would change to get there.*

---

## Can you explain this?

1. What are the three Vs, and where does our prototype sit on each?
2. Is this a Big Data project? Answer in three sentences.
3. Which part of our design is the clearest big-data idea, and why?
4. Why thresholds instead of machine learning?
5. Our system hits a wall at about 1,000 events per second. Where, and what fixes it?

### Answers

1. Volume, Velocity, Variety. Our volume is small (thousands of events), our velocity has the right shape but a small rate (continuous, a few per second), our variety is modest (six types, one schema).
2. Not by volume — thousands of events, not billions. But it is built on big-data principles: streaming ingestion, classification at write time, storage designed around access patterns, horizontal scaling, and validation at the boundary. We can name exactly what we would change to handle a thousand times more.
3. The sparse alerts index. Instead of storing everything and filtering on every read — paying to read 95% of records you discard — the filtering happens once, at write time. That is the same instinct as partitioning and pre-aggregation in any large system.
4. Explainability, data and defensibility. Our alert gives a reason an engineer can act on; a model gives a score. We have no labelled history to train on. And every teammate can defend a threshold under questioning.
5. The hot partition: all of a day's writes go to one partition key, and a partition sustains about 1,000 writes per second. The fix is a shard suffix on the partition key — ten partitions, queried in parallel — which touches only `keys.py` and `queries.py`.
