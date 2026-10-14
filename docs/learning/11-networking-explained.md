# Networking — explained

**Read after:** `00-start-here.md` · **Relevant code:** `infrastructure/terraform/vpc.tf`, `lambda.tf`

---

## 1. Why this document exists

In our initial design review, the professor specifically noted: **"VPC is missing, and group the Lambda functions according to business requirements."**

This document explains:
1. What a VPC, subnet, gateway endpoint, and security group are.
2. How we implemented a production-grade VPC without breaking our credit budget.
3. How our Lambda functions are organized across network boundaries according to business requirements.

---

## 2. Core networking concepts

- **VPC (Virtual Private Cloud)**: An isolated private software-defined network dedicated to your AWS account in a specific region.
- **Subnet**: A segment of a VPC's IP address range tied to a specific Availability Zone (AZ).
  - *Public Subnet*: Has a route table entry pointing to an Internet Gateway (`0.0.0.0/0` -> `igw-xxx`).
  - *Private Subnet*: Has **no route to the internet**. Resources inside cannot be reached from the internet, nor can they initiate connections to the internet.
- **Internet Gateway (IGW)**: A VPC component allowing bidirectional communication between resources in public subnets and the internet.
- **NAT Gateway**: A managed translation service allowing private subnet resources to reach the internet without exposing them inbound. **Crucial cost fact:** A NAT Gateway costs ~$0.045/hour (~$32/month), which would consume a third of our fixed student credit budget.
- **VPC Gateway Endpoint (Free / $0)**: An internal AWS route table target that redirects traffic intended for AWS services (like DynamoDB or S3) directly through the AWS private network, bypassing the internet entirely. It costs **$0.00**.
- **Security Group**: A stateful virtual firewall controlling inbound and outbound traffic at the network interface (ENI) level.

---

## 3. What we built: The CampusPulse VPC Architecture

Following review feedback, we configured our networking environment in `infrastructure/terraform/vpc.tf`:

```text
               VPC 10.20.0.0/16 (eu-west-3 Paris)
  ┌─────────────────────────────────────────────────────────────────┐
  │  Private Subnet A: 10.20.1.0/24 (eu-west-3a)                    │
  │     └─ api Lambda ENI ──┐                                       │
  │  Private Subnet B: 10.20.2.0/24 (eu-west-3b)                    │
  │     └─ api Lambda ENI ──┤  Security Group: No inbound,          │
  │                         │  Outbound 443 to DynamoDB only        │
  │  Private Route Table ───┴──► DynamoDB GATEWAY Endpoint ──► Table │
  │  VPC Flow Logs ──► CloudWatch Logs (7 days retention)           │
  │                                                                 │
  │  NO Internet Gateway · NO NAT Gateway · NO 0.0.0.0/0 Route       │
  └─────────────────────────────────────────────────────────────────┘
```

### Architectural Guarantees:
1. **Private Subnets Only**: Subnet A (`10.20.1.0/24` in `eu-west-3a`) and Subnet B (`10.20.2.0/24` in `eu-west-3b`).
2. **Zero Internet Route**: There is no Internet Gateway and no NAT Gateway. Any process running inside the VPC cannot send packets to external internet IP addresses.
3. **DynamoDB Gateway Endpoint**: Route table routes traffic for `com.amazonaws.eu-west-3.dynamodb` directly to DynamoDB. The endpoint policy is locked down to allow only `PutItem` and `Query` on *our* table (`campuspulse-dev-events`) and its indexes.
4. **Strict Security Group**: The Lambda security group has **zero inbound rules** and an egress rule allowing HTTPS (443) strictly to DynamoDB's managed prefix list.
5. **VPC Flow Logs**: Captures accepted and rejected IP packets for network-level auditability in CloudWatch Logs.

---

## 4. Compute Architecture: Grouping by Business Requirements

The professor's review emphasized **grouping Lambda functions to business requirements**.

Instead of 5 fragmented nano-functions split by technical CRUD verbs (`health`, `auth`, `ingest`, `query`, `stats`), we grouped compute into **two cohesive business domains** aligned with our security and network boundaries:

| Business Domain | Function | Placement | Responsibilities & Endpoints | Security & Network Boundary |
|---|---|---|---|---|
| **Public Identity & Access Gateway** | `campuspulse-dev-auth` | **Outside VPC** | User authentication, credential exchange via Cognito, role assertion (`admin` vs `student`).<br/>• `POST /login` | Reaches Cognito's public API directly ($0). **Holds zero database permissions**; cannot read or write campus telemetry. |
| **Protected Campus Operations Platform** | `campuspulse-dev-api` | **Inside VPC** (2 private subnets) | Real-time telemetry ingestion, anomaly classification, facility maintenance requests, comfort & energy analytics, and health.<br/>• `POST /events`<br/>• `POST /requests`<br/>• `GET /requests`<br/>• `GET /events`<br/>• `GET /alerts`<br/>• `GET /stats`<br/>• `GET /health` | Isolated from the public internet. Reaches DynamoDB strictly via the Gateway Endpoint. Code has **zero path to exfiltrate data** to external networks. |

---

## 5. How we solved the NAT Gateway cost dilemma

Most student architectures face a false dilemma:
- *Option A*: Build a VPC with private subnets and a NAT Gateway → Costs ~$32/month, burning the credit budget.
- *Option B*: Skip the VPC entirely → Fails cloud networking evaluation requirements (I3/D4).

**Our solution**: We deployed a custom VPC with private subnets and attached a **DynamoDB Gateway Endpoint**.
Because the data Lambda only communicates with DynamoDB, it requires no internet access. The Gateway Endpoint is a route table entry managed by AWS for **$0.00**.
The authentication Lambda, which must talk to Cognito, is placed outside the VPC where it accesses Cognito's public endpoint over HTTPS for free, without needing VPC Interface Endpoints or NAT.

Result: **Full enterprise private-network isolation at $0.00 additional cost.**

---

## 6. Self-test questions for defense

1. **Why does your VPC have no Internet Gateway or NAT Gateway?**
   Because our data Lambda (`api`) only needs to communicate with DynamoDB. DynamoDB is reached via a free Gateway Endpoint on AWS internal networking. Disabling internet egress guarantees that campus operational data cannot be exfiltrated.
2. **Why is the `auth` Lambda outside the VPC while `api` is inside?**
   This separates business concerns: `auth` interacts with Cognito's public authentication API. Placing it inside the VPC would require a NAT Gateway (~$32/mo) or a Cognito Interface Endpoint (~$16/mo). By keeping `auth` outside with zero database permissions, we maintain complete isolation with zero cost.
3. **What protects DynamoDB from unauthorized access if the endpoint has no internet?**
   The endpoint policy restricts access to *our* specific table and indexes, and IAM requires valid temporary credentials signed with `dynamodb:PutItem` or `dynamodb:Query`.
