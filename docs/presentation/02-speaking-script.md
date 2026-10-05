# Speaking Script

Only the words to be spoken. Nothing else.

Rehearse out loud and time it. Reading this aloud at a natural pace takes about fourteen minutes, which leaves a margin.

---

## SOMITHA — slides 1 to 6

Good morning. We are presenting CampusPulse 2026, a cloud-native platform for running a connected university campus. I am Somitha, and with me are Meha, Madhavan and MD.

A university campus produces thousands of measurements every day. How full each room is, how warm, how humid, how much electricity each building draws, whether a projector has failed, what students are asking for. Taken one at a time, almost none of those readings matters. The problem is that the handful which do matter are buried among the ones that do not, and no member of staff can watch thousands of readings to find them.

So the operations team has four practical questions. Which rooms are overloaded right now. Which buildings are consuming the most energy. Whether anything is abnormal. And which student requests are urgent. Our platform exists to answer those four questions, continuously, without anyone having to look for the answers.

Here is the architecture. A Python simulator stands in for the campus sensors. It sends events over HTTPS to Amazon API Gateway, which invokes one of five Lambda functions, which writes to DynamoDB. A dashboard hosted on S3 reads the same data back. Cognito handles identity, CloudWatch handles monitoring, and IAM controls what each component is permitted to do. Everything is in the Paris region, and everything is serverless.

We chose serverless for one reason above all others. Our workload is bursty — events arrive during a demonstration and then nothing for days. A virtual machine bills us every hour whether anyone is using it or not. Lambda bills per request and costs nothing while idle. We have one hundred credits that do not refill, so "costs nothing while idle" is the most valuable property available to us. To give one concrete number: a design with private subnets would need a NAT Gateway, which costs about thirty-two dollars a month to exist. That single component would have consumed a third of our budget doing nothing for us.

Now let me take one event through the whole system. The simulator invents a reading: fifty-eight people in Library-A room A203. It sends that over HTTPS with an authentication token. API Gateway checks the token before any of our code runs. Lambda then validates every field — the room must exist, the unit must be right, the value must be a plausible number, the timestamp must be recent. Then it classifies the severity. Room A203 holds forty-five people, so fifty-eight is a hundred and twenty-nine per cent of capacity, and that is critical.

And here is the part worth pausing on. The simulator sent that event marked "normal". Our server throws that away and computes the severity itself. A sensor must never be able to declare itself normal, because then anyone who can write an event can make a problem disappear. Meha will pick this up from the security side.

---

## MEHA — slides 7 to 9

Thank you. Security in this system is three independent layers, and a request has to get through all three.

The first is the token check at the edge. API Gateway verifies the signature, the issuer, the audience and the expiry of the token before any of our code runs. If the token is forged or expired, the caller gets a 401 and we never invoke a function — so an attacker flooding us with fake tokens costs us nothing.

The second layer is inside the function. The token carries the user's group, and each route checks it. If you have a valid token but the wrong role, you get a 403. The difference matters: 401 means we do not know who you are, and 403 means we know exactly who you are and the answer is still no.

The third layer is IAM, which decides whether a function may touch a resource at all. Even if an attacker controlled our code completely, they would still be limited to whatever that function's role allows.

We have two roles, and they really do behave differently. Operations staff can submit events and read alerts. Teaching staff can read events and statistics, and can raise a service request — but if they try to submit a sensor reading or read the alerts list, they get a 403. Madhavan will show you that live.

Least privilege is where this becomes concrete. We deliberately split the backend into five small functions instead of one, and each has its own role. The function that receives data from the internet can write to one table and cannot read anything at all. The functions that read cannot write. So if somebody found a flaw in our most exposed function, the worst they could do is add junk events. They could not read a single student's service request.

We also audited this rather than assuming it. We listed every AWS call the code makes and compared it against every permission granted: they match exactly, with no excess and no gaps. There are no AWS credentials anywhere in our code — the functions receive temporary credentials automatically. And we never grant the permission to scan the database, so if anyone later wrote a query that tried to, it would fail loudly rather than quietly getting slower every week.

---

## MD — slides 10 to 12

This is the dashboard the operations team actually uses. Five summary tiles across the top, then active alerts, room occupancy, energy by building, and the most recent events. It refreshes every ten seconds.

The page holds no data of its own. Everything on it comes from the API, which refuses to answer without a valid token. That is why we can host it in a public bucket safely — the bucket contains the page, not the campus.

One detail in it is a cost decision rather than a design one. Polling stops when the tab is hidden, and pauses entirely after fifteen idle minutes. A dashboard left open in a forgotten tab would make around seventeen thousand requests a day against an API we pay for per request. So it stops.

For monitoring, every function writes structured logs in JSON, each carrying a request identifier that also appears in the API's own access log. That means when something fails, one identifier ties the error, the function log and the gateway log together, and an investigation takes a minute instead of twenty.

We publish metrics using Embedded Metric Format, which means CloudWatch reads our metrics out of a specially shaped log line. We get the metrics without paying for a separate API call each time.

We have four alarms. Three watch the system: Lambda errors, server errors at the API, and a burst of alerts that suggests something campus-wide. The fourth watches the budget — an unusual number of invocations means something is looping, and on a pay-per-request service that is a spending problem days before it would appear on a bill.

On cost: nothing in this architecture bills by the hour. No EC2, no database instance, no load balancer, no NAT Gateway. We set log retention to seven days rather than leaving it at the default of never expiring. We use the Cognito tier that has a free allowance rather than the one that does not. Our budget alert deliberately excludes credits, because a normal cost budget on a credit-funded account reads zero right up until the credits are gone. Our estimate was under five dollars of the hundred, and our measured figure is on the slide.

---

## MADHAVAN — slides 13 to 15, including the demo

Before the demo, two things about how this scales and how we tested it.

Lambda and DynamoDB both scale horizontally and automatically. More events means more concurrent function instances, and we never configure that. But our design does have a ceiling, and we would rather tell you where it is than be asked. All of one day's events are stored under a single partition key, and a DynamoDB partition sustains roughly a thousand writes per second. Beyond that we would need to spread the writes across ten partitions by adding a shard suffix to the key, and read all ten in parallel. That change touches two files. We designed it; we did not build it, because our prototype is nowhere near that volume and building unused machinery would be harder to defend than describing it.

On testing, we have two layers. A hundred and thirty-one unit tests run in about a second with no AWS account at all, because we deliberately kept the logic free of cloud dependencies. Then forty-five tests run against the deployed system to check the wiring — the parts a unit test cannot see, like permissions and routing.

Two of those tests are really design guarantees rather than ordinary tests. One proves that no query our code can build will ever become a full table scan. The other takes a thousand events generated by the simulator and runs them through the real validator, so the simulator can never be the reason a live demonstration shows an error.

Which brings us to the demonstration.

[DEMO — the sequence is in `03-demo-runbook.md`]

So: an event entered the system, was judged critical by rules we wrote, was stored, appeared on the dashboard, and is traceable in the logs by a single identifier. And the same page shows a different thing to a different role.

---

## SOMITHA — slides 16 to 17

Four things we learned.

The first is that we should have deployed earlier. We built and tested a great deal before anything existed in AWS. The logic was genuinely verifiable on a laptop, but the deployment-shaped problems — permissions, cross-origin rules, token wiring — can only be found by deploying.

The second is that some bugs only exist visually. Our dashboard rendered the login form underneath the dashboard. Every element was present, the JavaScript ran without error, and the attribute that should have hidden it was set correctly — but a CSS rule silently overrode it. No test would have caught that. We found it by rendering the page and looking at it.

The third is about numbers. Several AWS pricing figures could not be read programmatically, so rather than quoting plausible-looking numbers we marked them as unverified in our report and wrote a script to resolve them properly. A report is believed because of what it admits, not because of what it claims.

And the fourth: we chose explainable threshold rules over machine learning. Our alert says "occupancy fifty-eight exceeds a hundred and twenty per cent of capacity forty-five". A model would say "anomaly score zero point eight seven". The first is something a campus engineer can act on, and it is something every one of us can defend.

To close. We built a working cloud-native platform: ingestion, storage, processing, two roles, a dashboard, monitoring, backup and cost control. It is secure because the architecture is shaped that way, not because security was added at the end. It cost under five dollars. And we can tell you exactly where it would break and what we would change.

Thank you. We are happy to take questions.
