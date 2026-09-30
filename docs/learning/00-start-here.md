# Start Here

If you have never used AWS, this is the right page. Read it once, slowly. Nothing else in the project assumes you have read anything before it.

---

## 1. What are we building?

A system that watches a university campus and tells the operations team what needs attention right now.

Sensors around NorthBridge University report things — how many people are in a room, the temperature, the humidity, how much electricity a building is using, whether a projector has failed — and students submit service requests. All of that lands in one place. A dashboard shows what is happening and, more importantly, what is **wrong**: a lecture hall over capacity, a lab at 31 °C, a building burning twice its normal electricity.

We do not have real sensors. We have a Python program that pretends to be them. That is normal and expected for this project — the spec says *simulated* sources.

## 2. Why are we building it?

The problem: a campus generates a constant stream of small facts, and none of them matter individually. What matters is the handful that are abnormal, and nobody can watch thousands of readings by hand. So we build something that collects everything, decides what is abnormal, and shows only that.

## 3. What is Cloud Computing?

**Simple:** renting somebody else's computers instead of buying your own, and paying only for what you use.

Before the cloud, running this system meant buying a server, putting it in a room, cooling it, patching it, and replacing it when it died — whether or not anyone was using it.

**Technical:** cloud providers run enormous data centres and rent their capacity through APIs. Three properties matter here:

- **On-demand** — you create a resource with an API call, in seconds.
- **Elastic** — capacity follows demand up and down automatically.
- **Pay-per-use** — you are billed for what you consume, and some services bill nothing while idle.

That last one is why this project can exist on a student budget.

## 4. What is AWS?

Amazon Web Services, the largest cloud provider, offering roughly two hundred services. **We use seven.** Ignore the other hundred and ninety-three — they are not on the exam and they are not in our project.

| Service | What it does for us |
|---|---|
| **API Gateway** | The front door. Receives every request from the internet |
| **Lambda** | Runs our code, but only when a request arrives |
| **DynamoDB** | Stores the events |
| **Cognito** | Handles users, passwords and roles |
| **S3** | Serves the dashboard's files |
| **CloudWatch** | Logs, metrics and alarms — how we see what happened |
| **IAM** | Decides which part of our system may touch which other part |

## 5. What is Big Data?

**Simple:** data that is too big, too fast or too messy for one computer and a spreadsheet.

The classic three Vs:

- **Volume** — how much there is
- **Velocity** — how fast it arrives
- **Variety** — how many different shapes it comes in

**Be honest about this at the oral.** Our prototype handles thousands of events, not billions. It is not big data by volume. What it *is* is a system built the way big-data systems are built: events arrive continuously rather than in batches, they are classified as they arrive rather than in an overnight job, storage is chosen around known access patterns rather than around SQL convenience, and every component scales horizontally. If the campus grew a thousand-fold, the *design* would hold — we would add sharding to the partition key and pre-aggregate counters, and we can describe exactly how. Claiming our prototype processes big data would be false; claiming it demonstrates the principles is true, and it is the better answer.

## 6. The analogy — and where it stops

Think of the system as a building with staff:

| Our system | The building |
|---|---|
| Simulator | Sensors bolted to the walls |
| API Gateway | The reception desk: checks your badge, directs you |
| Lambda | A worker hired for the exact seconds they are working |
| DynamoDB | The filing system |
| Cognito | The security guard who issues badges |
| CloudWatch | The control room with the camera feeds |
| IAM | The key cabinet — each key opens one door |
| Dashboard | The screen in the control room |

**Where the analogy breaks down**, and you should know this before someone asks:

- A real receptionist handles one visitor at a time. API Gateway handles thousands simultaneously.
- A real worker sits idle between tasks and still gets paid. Lambda does not exist between requests, and costs nothing.
- A real filing cabinet lets you rummage through every drawer. DynamoDB does not — you must know the label in advance. That constraint is why our data model looks the way it does.
- A real guard recognises faces. Cognito verifies a cryptographic signature; it has no memory of you between requests.

## 7. How does data move through the system?

```text
Simulator  --(1)-->  API Gateway  --(2)-->  Lambda  --(3)-->  DynamoDB
                          |                    |
                     checks badge          writes log
                          |                    |
                          v                    v
                        (401)             CloudWatch
                                               ^
Browser  <--(5)--  Dashboard  <--(4)--  Lambda -+
```

1. The simulator sends one reading as JSON over HTTPS.
2. API Gateway checks the token. Bad token → 401, and our code never runs.
3. Lambda validates the reading, decides its severity, stores it.
4. The dashboard asks for recent events, alerts and statistics.
5. An abnormal reading shows up as a red row.

The full version, with all fourteen stages and every failure mode, is in `docs/architecture/06-data-flow.md`.

## 8. What should I learn first?

Follow `learning-path.md`. In short: this page → the architecture diagram → APIs and JSON → then the one component you own.

## Can you explain this?

1. What does our platform actually do for the campus operations team?
2. Name three of our seven AWS services and what each one is for.
3. Why is "pay only for what you use" so important for this particular project?
4. Is this a big-data system? Answer honestly, in two sentences.
5. Where does the reception-desk analogy stop being accurate?

### Answers

1. It collects readings from across campus, decides which are abnormal, and shows the abnormal ones on a dashboard so somebody can act — an overloaded room, an overheating lab, a building using double its normal power.
2. Any three of: API Gateway (public entry point and token checks), Lambda (runs our code per request), DynamoDB (stores events), Cognito (users, passwords, roles), S3 (serves the dashboard), CloudWatch (logs, metrics, alarms), IAM (permissions between components).
3. Because we have a fixed 100-credit budget that does not refill. Services that bill by the hour would drain it while we sleep; our services cost nothing when nobody is sending events.
4. Not by volume — we handle thousands of events, not billions. But it is built on big-data principles: continuous ingestion, classification at arrival, storage designed around access patterns, and horizontal scaling — and we can describe exactly what we would change to handle a thousand times more.
5. A receptionist serves one person at a time and a worker is paid while idle; API Gateway is massively concurrent and Lambda does not exist between requests. And unlike a filing cabinet, DynamoDB cannot be rummaged through — you must know the key in advance.
