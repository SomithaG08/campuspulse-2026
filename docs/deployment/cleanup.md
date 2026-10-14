# Cleanup — deleting everything

Required by spec §8: *stop or delete unused resources after testing*. Rehearse this **once, early**, not for the first time at the end of the project.

## Before you delete anything

Deletion is permanent. There is no recycle bin.

1. **Export the evidence you still need.** Screenshots, logs, and a dump of the table if the report references its contents:
   ```bash
   aws dynamodb scan --table-name campuspulse-dev-events \
     --output json > docs/evidence/final-table-dump.json
   ```
   *(The one and only place a `Scan` is acceptable: exporting a finished table, once.)*
2. **Save the CloudWatch logs you cite in the report** — deleting the log group deletes them.
3. **Check your `terraform output` is recorded** somewhere outside the state file.

## The easy path

```bash
cd infrastructure/terraform
terraform destroy
```

Read what it lists before typing `yes`. It should destroy about 75 resources and nothing you did not expect.

Since October 2026:
- **The S3 bucket and the backup vault have `force_destroy`**, so Terraform empties them itself (every object version and every recovery point). Export anything you need *before*.
- **The VPC takes a while.** The `api` function's network interfaces are released asynchronously after the function is deleted; `destroy` can wait 20-40 minutes on the security group and subnets. Let it finish rather than interrupting it.
- **Unsubscribe is automatic**: the SNS subscriptions are deleted with the topic.

## The manual path

If the state file is lost or `destroy` fails, delete by hand in this order:

1. Empty, then delete the S3 bucket
2. Delete the API and the two Lambda functions
2b. Delete the AWS Backup selection, plan, then the recovery points and the vault
2c. Delete the VPC endpoint, flow log, security group, subnets, route table, then the VPC (after the Lambda's network interfaces are gone)
2d. Delete the SNS topic
3. Delete the CloudWatch log groups, alarms and dashboard
4. Delete the DynamoDB table — **export first if you need the data**
5. Delete the Cognito user pool (this deletes the users with it)
6. Detach and delete the IAM policies, then the roles (api, auth, backup, flow-logs)
7. Delete the budget

Roles and policies come last because other resources reference them.

## Confirm it is really gone

```bash
aws dynamodb list-tables --region eu-west-3
aws cognito-idp list-user-pools --max-results 20 --region eu-west-3
aws s3 ls
aws lambda list-functions --region eu-west-3 --query 'Functions[].FunctionName'
aws logs describe-log-groups --region eu-west-3 --query 'logGroups[].logGroupName'
aws ec2 describe-vpcs --region eu-west-3 --filters Name=tag:Project,Values=CampusPulse2026
aws backup list-backup-vaults --region eu-west-3
aws sns list-topics --region eu-west-3
```

Nothing named `campuspulse` should appear in any of them.

**Then watch the credit balance for 24 hours.** A balance that is still moving means something survived. Find it in Cost Explorer, grouped by service.

## Keep the budget alert

Delete everything else, but consider leaving the budget in place until the account is closed. It costs nothing to keep and it is the last thing that would warn you if something you thought was deleted is still running.
