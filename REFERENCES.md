# References

Every external source used, cited as required by the spec (§16). Add to this file *as you use a source*, not at the end.

## Course material

- Cloud Computing Final Project brief, S2 2026 — *Cloud Native Smart Campus Operations Platform*, Big Data & Cloud Computing, EPITA (the project specification; primary source of truth).
- Course slides and labs: `Class Notes/` (Cloud Computing Part 1, LAB01-07, Big Data CH1-CH2).

## AWS documentation and pricing — all consulted 2026-09-22

- AWS Free Tier — https://aws.amazon.com/free/
- AWS Free Tier FAQs — https://aws.amazon.com/free/free-tier-faqs/
- "AWS Free Tier now offers $200 in credits and 6-month free plan" (16 Jul 2025) — https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/
- Free Tier in the new AWS experience — https://docs.aws.amazon.com/accounts/latest/reference/bcm-lite-free-tier.html
- AWS Lambda pricing — https://aws.amazon.com/lambda/pricing/
- Amazon API Gateway pricing — https://aws.amazon.com/api-gateway/pricing/
- Amazon DynamoDB pricing — https://aws.amazon.com/dynamodb/pricing/
- Amazon Cognito pricing — https://aws.amazon.com/cognito/pricing/
- Amazon CloudWatch pricing — https://aws.amazon.com/cloudwatch/pricing/
- Amazon S3 pricing — https://aws.amazon.com/s3/pricing/

*To add as they are used: the DynamoDB developer guide sections on key design and secondary indexes, the Lambda developer guide on the Python runtime, the Cognito developer guide on user pools and groups, and the API Gateway guide on HTTP APIs and JWT authorizers.*

## Libraries

| Library | Used for | Licence |
|---|---|---|
| `boto3` | AWS SDK for Python (DynamoDB, Cognito) | Apache-2.0 |
| `requests` | HTTP calls from the simulator | Apache-2.0 |
| `pytest` | Test runner | MIT |

*Versions are pinned in the relevant `requirements.txt` once written.*

## Reused code

None so far. **Any code copied or adapted from a tutorial, answer or repository must be listed here with its URL and what was changed**, before it is committed.

## AI assistance

The team used an AI assistant during planning and drafting. The architecture decisions, the implementation and the report are the team's own: every generated draft was reviewed, edited and verified by the member who owns that component, and no team member presents a component they did not build and cannot explain. Factual claims about AWS pricing and free-tier limits were checked against the AWS pages cited above rather than accepted from the assistant.
