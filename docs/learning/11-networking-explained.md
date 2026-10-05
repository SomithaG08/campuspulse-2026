# Networking — explained

**Read after:** `00-start-here.md` · **Relevant code:** none, and that is the point

---

## 1. Why this document exists

**Our architecture has no VPC, no subnets and no security groups.** That is a decision, not an omission — and you will be asked about it, because every cloud course teaches VPCs.

This page teaches the concepts properly, shows what our system *would* look like with them, and explains why we deliberately do not have one.

## 2. The concepts, from zero

**VPC (Virtual Private Cloud)** — your own private network inside AWS. Think of a building you rent: the address space is yours, and nothing gets in unless you open a door.

**Subnet** — a floor in that building, tied to one Availability Zone.
- **Public subnet** — has a route to the internet gateway. Things here can be reached from the internet.
- **Private subnet** — no route to the internet. Things here are reachable only from inside the VPC.

**Internet Gateway** — the front door, attached to the VPC. Free.

**NAT Gateway** — the one-way back door. It lets a machine in a *private* subnet reach out to the internet (to download updates, call an API) **without being reachable from it**. It costs about **$0.045 per hour plus per-GB**, which is roughly **$32 a month to exist**.

**Security group** — a firewall around a resource: "allow TCP 443 from anywhere, allow TCP 22 from my office only". Stateful: a reply to an allowed request is automatically allowed back.

**Network ACL** — a firewall around a *subnet*. Stateless, so you must allow both directions. Most projects use security groups and leave ACLs alone.

## 3. What CampusPulse would look like with a VPC

If we had built this on EC2 and RDS:

```text
                        Internet
                            │
                   ┌────────▼─────────┐
                   │ Internet Gateway │
                   └────────┬─────────┘
   ┌───────────────────── VPC ──────────────────────┐
   │  PUBLIC SUBNET (AZ-a)      PUBLIC SUBNET (AZ-b)│
   │   ┌──────────────┐          ┌──────────────┐   │
   │   │ Load balancer│          │  NAT Gateway │   │ ← $32/month
   │   └──────┬───────┘          └──────┬───────┘   │
   │          │                         │           │
   │  PRIVATE SUBNET (AZ-a)     PRIVATE SUBNET (AZ-b)│
   │   ┌──────▼───────┐          ┌──────▼───────┐   │
   │   │ EC2: our API │          │ RDS database │   │ ← hourly, 24/7
   │   │  SG: 443 from│          │ SG: 5432 from│   │
   │   │  the LB only │          │  the EC2 SG  │   │
   │   └──────────────┘          └──────────────┘   │
   └────────────────────────────────────────────────┘
```

That is a perfectly good architecture. It is also three resources that bill by the hour whether or not anybody uses them, on a budget of 100 non-renewable credits.

## 4. What we built instead

```text
   Internet ──HTTPS──► API Gateway ──► Lambda ──► DynamoDB
                            │
                   JWT authorizer + IAM
```

Lambda, API Gateway, DynamoDB, Cognito and S3 are **AWS-managed services**. They run in AWS's own network, not in one we rent. We never place a server inside a subnet, so there is no subnet to configure and no NAT Gateway to pay for.

**Our network boundary is not a subnet — it is IAM plus the JWT authorizer.** The equivalences map cleanly:

| VPC concept | Our equivalent |
|---|---|
| Public subnet | API Gateway: the only internet-facing component |
| Private subnet | Lambda and DynamoDB: no public endpoint; reachable only through the API or IAM |
| Security group | The Lambda resource policy — only API Gateway may invoke |
| Network ACL | IAM policies — deny by default, allow by exception |
| Internet Gateway | The managed HTTPS endpoint |
| NAT Gateway | **Not needed.** Lambda reaches AWS services over the AWS network |
| Bastion host | **Not needed.** There is no server to log into |

The spec (§9) asks the diagram to show networking "including VPC, subnets, security groups, **or equivalent concepts**". The right-hand column is our equivalent concepts, and the diagram draws them as trust zones.

## 5. The cost argument, stated plainly

A NAT Gateway is roughly **$32 a month for a component that does nothing we need**. On 100 credits that is a third of the budget, spent on idling.

This is the most expensive single mistake available to a student cloud project, and avoiding it is not luck — it follows directly from choosing managed services over servers.

## 6. Is "no VPC" less secure?

A fair question, and the honest answer is: **different, not worse, for this system**.

A VPC protects things that listen on a network. Our components do not listen on a network — they are invoked by AWS. There is no port to scan, no SSH to brute-force, no unpatched OS. The attack surface is the API, and that is protected by TLS, the JWT authorizer, IAM, input validation and throttling.

What a VPC *would* add that we do not have: private connectivity to DynamoDB via a VPC endpoint (our traffic already stays on the AWS network and is encrypted, but a VPC endpoint makes that explicit and auditable), and network-level isolation if we later ran something that genuinely listens.

**If this platform grew to need a database with a network protocol, or a long-running service, a VPC would become the right answer.** Knowing the trigger for that change is better than claiming we will never need one.

---

## Can you explain this?

1. What is a VPC, and what is a subnet?
2. What does a NAT Gateway do, and why do we not have one?
3. Our architecture has no security groups. What plays that role?
4. Is "no VPC" a security weakness here?
5. What would make us need a VPC later?

### Answers

1. A VPC is your own private network inside AWS. A subnet is a slice of it tied to one Availability Zone — public if it has a route to the internet gateway, private if it does not.
2. It lets resources in a private subnet make outbound internet connections without being reachable inbound. We have no private subnet and no server needing outbound access — and it costs about $32 a month to exist, which is a third of our credit budget.
3. The Lambda resource policy, which permits only API Gateway to invoke our functions, plus IAM policies that decide what each function may touch. Deny by default, allow by exception — the same shape as a firewall rule, enforced at the API layer instead of the network layer.
4. Different, not worse. A VPC protects things that listen on a network; nothing of ours listens. There is no port to scan and no OS to patch. Our attack surface is the API, protected by TLS, the JWT authorizer, IAM, validation and throttling.
5. A database speaking a network protocol, a long-running service, or a requirement for private connectivity via VPC endpoints. The trigger is: the moment we run something that listens on a port.
