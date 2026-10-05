# Team Knowledge Check

**How to use it:** one person asks, the others answer **out loud, without notes**. Then swap. Do it twice — once a week before, once the day before.

The brief requires every member to explain both the architecture and the implementation. In an oral exam the weakest answer sets the impression, so the aim is not that one person aces it.

---

## Beginner — everyone

1. What is cloud computing, in two sentences?
2. What is AWS, and how many of its services do we use?
3. What is an API?
4. What does our platform actually do for the campus operations team?
5. What is AWS Lambda, and what makes it different from a server?
6. What is a database, and which one do we use?
7. What is JSON?

**Answers.** 1 — Renting computing over the internet on demand and paying for what you use, instead of buying and maintaining machines. 2 — Amazon Web Services, the largest cloud provider; we use seven of its services. 3 — An agreed set of requests one program will accept from another, and the answers it gives back. 4 — Collects readings from across campus, decides which are abnormal, and shows those so somebody can act. 5 — A service that runs your function when a request arrives; a server runs continuously and bills by the hour whether used or not. 6 — A system for storing and retrieving data; we use DynamoDB, a NoSQL key-value store. 7 — A text format for structured data; every request and response in our API.

## Intermediate — everyone

8. Why does the simulator send events through API Gateway rather than writing to the database directly?
9. Why DynamoDB rather than a relational database?
10. What does Cognito do for us?
11. What does IAM control, and how is that different from what Cognito controls?
12. What does CloudWatch give us, and name our four alarms.
13. What is a cold start?
14. Why is there no VPC?

**Answers.** 8 — Because the API is where validation, severity rules and access control live. Direct writes would need database credentials on every client and would bypass all of it. 9 — Our access patterns are fixed and known, DynamoDB answers each in one query, and it costs nothing while idle; RDS bills hourly and needs a VPC. For arbitrary analytical queries a relational store would be better, and we say so. 10 — Stores users, verifies passwords, manages groups, issues signed tokens — so our code never handles a password. 11 — IAM controls what our AWS components may do to AWS resources; Cognito controls which humans may use the API. 12 — Logs, metrics, alarms and a dashboard. Alarms: ingest errors, API 5xx, alert burst, invocation ceiling. 13 — The 1-3 second delay when Lambda must build a new execution environment; afterwards invocations are milliseconds. 14 — Nothing of ours listens on a network; all services are managed. Our boundary is IAM plus the token check, and a NAT Gateway would cost ~$32/month for nothing.

## Architecture — everyone

15. Trace one event from the simulator to the dashboard, naming every component.
16. What happens if a Lambda fails?
17. How does the system scale, and where does it stop scaling?
18. How is the API protected? Name the three layers and their failure codes.
19. How do we control AWS cost? Give four specific decisions.
20. What is a sparse index and why do we have one?
21. Why is there no `Scan` anywhere, and what enforces that?
22. What are our RPO and RTO, and where do those numbers come from?
23. The client sends `"severity": "normal"` on an obviously critical event. What happens, and why does it matter?

**Answers.** 15 — Simulator → HTTPS → API Gateway → JWT authorizer → Lambda `cp-ingest` → validate → classify → DynamoDB (plus the sparse alert index) → CloudWatch log and metric → dashboard polls `/stats` and `/alerts` → red row. 16 — The caller gets a 500 with a request id, the detail goes to CloudWatch, an alarm fires, and nothing already written is lost. 17 — Lambda adds concurrent environments and DynamoDB splits partitions, both automatically. It stops at roughly 1,000 writes/second because one day's events share one partition key; the fix is a ten-way shard suffix. 18 — API Gateway's JWT authorizer (401), the function's group check (403), IAM on every AWS call (AccessDenied). 19 — Any four of: nothing bills hourly; no NAT Gateway; HTTP API instead of REST; 7-day log retention; 30-day TTL; Cognito Essentials; EMF metrics; throttling; dashboard polling pauses; simulator interval floor. 20 — An index that only contains items carrying its key attributes. `cp-ingest` writes the alert key only for abnormal events, so `/alerts` reads an index of alerts instead of reading the day and discarding 95%. 21 — Because a scan reads the whole table and worsens as it grows. Enforced by the key design, by a unit test, and by IAM never granting the permission. 22 — RPO effectively zero because PITR restores to any second in 35 days; RTO measured from an actual restore rehearsal, not estimated. 23 — The server discards it and recomputes from the value and the room's capacity. Otherwise anyone able to write an event could mark a real problem as normal and hide it.

## Your own component — each member

24. What does your component do, in 60 seconds, without notes?
25. What is the hardest part of it to get right?
26. What would you change if you rebuilt it?
27. Which file would you open first if it broke?

## Presentation

28. Why did we choose this architecture? Give both the cost reason and the learning reason.
29. What is the most important thing to say about security?
30. What did the project cost, and how do you know?
31. What is the biggest limitation of what we built?
32. An examiner says *"you did not really implement X, did you?"* — what do you say?

**Answer to 32.** If it is true: *"That is right — it is designed and documented, and we did not build it."* Our documentation already marks everything as Implemented, Configured or Planned for exactly this reason. Never invent. An examiner who catches one invention discounts everything else.

---

## Passing the check

Each member should be able to:

- [ ] Draw the architecture on a whiteboard, unaided
- [ ] Trace one event end to end, naming each component
- [ ] Explain their own component in 60 seconds without notes
- [ ] Explain the other three in one sentence each
- [ ] Name three cost decisions and the reason for each
- [ ] Name one real limitation of the system without being prompted

**That last one separates a good grade from a great one.** Every system has limits; knowing yours is the difference between a student who built something and one who understands it.
