# Learning Path — zero to "I can explain this project"

Ten steps. Roughly 6-8 hours of reading and doing, spread over the project — not a weekend. Steps 1-4 are for everyone. Steps 5-8 go deep only on **your** component; skim the others. Steps 9-10 are for everyone again.

Tick them off. If you cannot answer a step's questions, do not move on — it will only get harder.

---

## Step 1 — What is this? (30 min)

**Read:** `docs/learning/00-start-here.md`
**Do:** nothing yet.
**Understand:** what the platform does, what the seven services are for, and the honest answer about big data.
**Answer:**
1. What problem does CampusPulse solve for the operations team?
2. Name our seven AWS services and one sentence each.
3. Why would an always-on server be a bad choice for us specifically?

## Step 2 — The architecture (45 min)

**Read:** `docs/architecture/02-diagram.md`, then `01-architecture-decisions.md` (AD-0 to AD-4 at minimum).
**Do:** draw the diagram yourself, from memory, on paper. Compare. Redraw what you missed.
**Understand:** the three trust zones and what enforces each boundary.
**Answer:**
1. Trace one event from the simulator to the dashboard, naming every component it touches.
2. Why serverless instead of EC2? Give the cost reason and the learning reason.
3. Why do we have five Lambda functions instead of one?

## Step 3 — APIs and JSON (45 min)

**Read:** `docs/architecture/05-api-contract.md`, plus the API and JSON entries in the glossary.
**Do:** install `curl` or open Postman. Call any public API — `curl https://api.github.com/users/github` will do — and read the JSON that comes back.
**Understand:** method, path, headers, body, status code.
**Answer:**
1. What is the difference between 401 and 403? Which does a `staff` token get on `/alerts`, and why?
2. What does `Authorization: Bearer <token>` do?
3. Why is `POST /events` a POST and `GET /stats` a GET?

## Step 4 — The data model (45 min)

**Read:** `docs/architecture/04-data-model.md` in full, including the worked example.
**Do:** take the example event and work out its `pk`, `sk`, `gsi1pk` and `gsi2pk` by hand. Then change `value` to 20 and work out which keys disappear.
**Understand:** why "newest first" is free, and what a sparse index buys us.
**Answer:**
1. Why is the date in the partition key?
2. Why does a `normal` event not appear in the alerts index?
3. What is wrong with `Scan`, and why does our design not need one?

---

*Steps 5-8: read your own component's section properly; skim the rest. Ownership is in `docs/requirements/06-team-assignment.md`.*

## Step 5 — Lambda and the backend (1 h) — *Somitha*

**Read:** `03-services-explained.md` → Lambda; `06-data-flow.md` stages 5-12; the handler code once it exists.
**Do:** open the Lambda console, run a test invocation, read the `REPORT` line at the end of the log.
**Answer:** What is a cold start and how do we handle it? What does the handler receive and return? Where does the severity decision happen, and why do we override what the device sent?

## Step 6 — DynamoDB (1 h) — *Somitha, with MD*

**Read:** `03-services-explained.md` → DynamoDB; the data model again, now that you have seen the code.
**Do:** in the console, run each of the five access patterns against the real table.
**Answer:** What must every query supply? What is on-demand capacity and why did we choose it over provisioned? What is the known limit of our key design, and what would fix it?

## Step 7 — Authentication and security (1 h) — *Meha*

**Read:** `03-services-explained.md` → Cognito and IAM; `05-api-contract.md` → the permission matrix; the threat model once written.
**Do:** log in as both users. Paste each token into jwt.io and find `cognito:groups`. Then call `/alerts` with the `staff` token and watch the 403 arrive.
**Answer:** Name the three enforcement layers in order. Why does our code never see a stored password? What does least privilege mean *concretely* for `cp-ingest`?

## Step 8 — Monitoring (45 min) — *MD*

**Read:** `03-services-explained.md` → CloudWatch; the troubleshooting guide once written.
**Do:** find the log line for one specific event using its `request_id`. Then deliberately push an alarm into ALARM and screenshot it.
**Answer:** Difference between a log, a metric and an alarm? Why is log retention set to 7 days? A request returned 500 — what do you look at first?

---

## Step 9 — Run the whole thing yourself (1 h) — *everyone*

**Do, from the deployment guide, on your own machine:**
1. Open the dashboard and log in.
2. Start the simulator.
3. Watch events appear.
4. Force an abnormal event and watch the alert turn red.
5. Find that same event in DynamoDB.
6. Find its line in CloudWatch Logs.
7. Call one endpoint with `curl` and one with the wrong role.

**Nobody presents this project without having done step 9 end to end at least once.** Reading about a system and having run it are different states of knowledge, and an examiner can tell them apart in about two questions.

## Step 10 — Practise the presentation (1 h + rehearsals) — *everyone*

**Read:** your section's spoken explanation, and `06-data-flow.md` → "the short version".
**Do:** say your part out loud, timed, without slides. Then have a teammate ask you three questions you did not prepare for.
**Answer, cold:** Why this architecture? What happens if a Lambda fails? How does it scale? How is the API protected? What does it cost and how do you know? What is your RPO and RTO? What would you do differently?

---

## Self-check before the oral

If you can do these, you are ready:

- [ ] Draw the architecture on a whiteboard, unaided
- [ ] Trace one event from sensor to red row, naming each component
- [ ] Explain your own component in 60 seconds without notes
- [ ] Explain the other three components in one sentence each
- [ ] Say why we chose our stack *and* what we rejected, with reasons
- [ ] State our cost, where the number came from, and what protects the budget
- [ ] Name our system's real limits without being prompted

That last one separates a good grade from a great one. Every system has limits; knowing yours is the difference between a student who built something and a student who understands it.
