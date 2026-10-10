# Cloud Ops Copilot: Free-Tier Project Overview

Project plan, version 1, October 2026

## 1. What you are building

Cloud Ops Copilot is a chat assistant that answers questions about your AWS logs, for example: why did the checkout Lambda fail at 2 pm? It pulls logs from CloudWatch through a plugin system, splits them into chunks, turns them into embeddings, stores them in a FAISS index on S3, and uses an Amazon Bedrock model to answer from the retrieved log lines, with citations.

Goals:

- Learn the core AWS services by using them together, not in isolation.
- Learn Python-based RAG properly: chunking, embeddings, retrieval, evaluation.
- Finish with a portfolio piece: repository, architecture diagram, evaluation results and a demo recording.

Non-goals: multi-user login, high availability, autoscaling, very large log volumes.

## 2. Budget rules

New AWS accounts on the Free Plan get $100 in credits, up to $200 after onboarding tasks, valid for up to six months. On top of that, a set of services stays free within monthly limits. This project uses only services from those two groups.

| Group | Services used | How it is billed |
| --- | --- | --- |
| Always free within monthly limits | Lambda, DynamoDB, EventBridge schedules, SNS, SSM Parameter Store (standard), CloudWatch alarms and dashboards, IAM, CloudFormation and CDK | $0 at this scale |
| Small, covered by credits | EC2 t3.micro, EBS, public IPv4 address, S3, ECR, CloudWatch Logs, Bedrock tokens | A few dollars in total |

Excluded on purpose because they cost real money for no extra learning: ECS Fargate, Application Load Balancer, NAT Gateway, OpenSearch Serverless, Bedrock Knowledge Bases (their default vector store is expensive), RDS and Aurora, Secrets Manager, API Gateway, Kendra.

### Estimated spend

These are estimates. Confirm each line in the AWS Pricing Calculator for your region.

| Item | 14 days |
| --- | --- |
| EC2 t3.micro running 24/7 | about $3.50 |
| Public IPv4 address | about $1.70 |
| EBS 20 GB gp3 volume | about $0.80 |
| Bedrock: Nova Lite answers plus Titan embeddings, a few thousand requests | about $1 to $3 |
| S3, ECR, CloudWatch Logs, DynamoDB, Lambda, EventBridge | about $0 to $1 |
| **Total** | **about $8 to $10** (roughly $15 to $20 for a full month) |

The $150 limit is never close. The real risk on a Free Plan account is running out of credits early, because the account then closes, so the guardrails below matter more than the total.

### Guardrails

- Create AWS Budgets with email alerts at $10, $25 and $50.
- Check Billing, then Credits, once a week.
- Tag every resource with project=cloudops-copilot so leftovers are easy to find.
- Terminate the EC2 instance when you are done. A stopped instance still pays for its disk and IP.
- Never create a NAT Gateway, OpenSearch domain or RDS database.

## 3. Architecture

```
 Developer laptop              GitHub
  code + Docker ---push--->  Actions (OIDC) --build/push--> ECR (private)
                                                              |
                                                              | docker pull
                                                              v
 Your browser --HTTP from your IP only--> EC2 t3.micro (default VPC, public subnet)
                                            |-- Streamlit UI   :8501
                                            |-- FastAPI        :8000 (/chat, /health)
                                            |-- Index loader (reloads when S3 index changes)
                                                 |        |            |
                                                 v        v            v
                                              S3 bucket  DynamoDB    Bedrock
                                              (FAISS     (chat       Nova Lite: answers
                                               index +   history)    Titan v2: embeddings
                                               metadata)
                                                 ^
                                                 | writes new index version
 EventBridge schedule (every 30 min) --> Lambda: log refresher
                                            | reads new logs since checkpoint
                                            v
                                        CloudWatch Logs <-- Lambda: sample log generator (every 5 min)

 CloudWatch alarms --> SNS email
 SSM Parameter Store: model IDs, bucket name, config
 SSM Session Manager: shell access, no SSH, no open port 22
```

## 4. Services and what each one teaches

| Service | Role in the project | What you learn |
| --- | --- | --- |
| EC2 | Runs the app container | Virtual machines, security groups, instance roles |
| ECR | Private image registry | How images move from build to deploy |
| S3 | Stores the FAISS index and checkpoints | Durable shared storage, versioning, bucket policies |
| Lambda | Log generator and log refresher | Event-driven code, layers, timeouts, memory |
| EventBridge | Schedules the Lambdas | Cron in the cloud |
| CloudWatch Logs and alarms | Log source and monitoring | Observability, filter queries, alarms |
| SNS | Email alerts from alarms | Notifications |
| DynamoDB | Chat history per session | Key-value design, on-demand access |
| IAM | Roles for EC2 and Lambdas | Least privilege |
| SSM Parameter Store | Config and model IDs | Configuration without redeploys |
| SSM Session Manager | Shell access to EC2 | Access without SSH keys |
| Bedrock | Answers and embeddings | Managed model inference, Converse API |
| CDK (Python) | Infrastructure as code | Repeatable deploys, one-command teardown |
| GitHub Actions with OIDC | CI/CD into AWS | Short-lived credentials, no stored keys |

## 5. Key design decisions

1. **Embeddings through Bedrock Titan, no PyTorch.** Images stay small, Lambda packages stay small, and the 1 GB micro instance has enough memory.
2. **Converse API with the model ID in configuration.** Swapping Nova Micro, Nova Lite or Nova 2 Lite is a config change, which also makes model comparison easy.
3. **Incremental index refresh.** The refresher keeps a checkpoint (last processed timestamp) in S3, embeds only new records, appends them to the current index, and writes a new version under a versioned prefix. A small latest pointer file tells the app which version to load. Logs older than 7 days are dropped when the index is rebuilt weekly.
4. **Default VPC, public subnet, no NAT.** The security group allows the app ports only from your own IP. Shell access uses Session Manager, so port 22 stays closed. Port forwarding through Session Manager can replace public access entirely.
5. **Parameter Store, not Secrets Manager.** Roles replace API keys, so there are no secrets to store.
6. **Everything in CDK.** Build the first version by hand to learn, then recreate it in code so that cdk destroy removes it all.

## 6. Plugin design

Every log source implements one small interface, so adding a source never touches the RAG code.

```python
class LogPlugin(ABC):
    name: str

    @abstractmethod
    def fetch(self, since: datetime, until: datetime) -> Iterator[LogRecord]:
        ...
```

A LogRecord holds id, timestamp, source, service, level, message and a dictionary of extra attributes. Plugins are registered by name in configuration.

- Phase 1: CloudWatchPlugin for Lambda logs.
- Phase 2: S3AccessLogPlugin for S3 server access logs.

## 7. RAG pipeline

1. **Ingest and normalize.** Plugins yield LogRecords in one common shape.
2. **Chunk.** Group records by request ID where present, otherwise by service and 60-second window, targeting about 300 to 500 tokens per chunk. Keep service, level and time range as metadata.
3. **Embed.** Titan Text Embeddings v2 in batches, with exponential backoff for throttling.
4. **Store.** A FAISS flat inner-product index over normalized vectors, plus a JSON file holding chunk text and metadata.
5. **Retrieve.** Embed the question, take the top 8 chunks, and apply optional filters (service, level, time range) parsed from the question.
6. **Generate.** The prompt tells the model to answer only from the supplied logs, cite log IDs, and say so when the logs do not contain the answer.
7. **Remember.** The last 6 turns per session are kept in DynamoDB.

### Evaluation

Write 25 questions with known answers against generated logs. Include injected failures such as timeouts, permission errors and cold-start spikes. Measure:

- Retrieval: is the right chunk in the top 8 (recall at k)?
- Answer: does it cite correct log IDs, and does it refuse when the answer is absent?

Run the same set against Nova Micro, Nova Lite and Nova 2 Lite and keep the results table for the README.

## 8. Repository layout

```
cloudops-copilot/
  plugins/        base.py, cloudwatch_plugin.py, s3_access_plugin.py
  core/           models.py, chunker.py, embedder.py, vector_store.py
  agent/          retriever.py, rag_agent.py, memory.py
  api/            server.py
  ui/             app.py
  lambdas/        log_generator/, log_refresher/
  infra/          CDK app in Python
  eval/           questions.json, run_eval.py, results/
  tests/
  Dockerfile
  docker-compose.yml
  pyproject.toml
  README.md
```

## 9. Build plan

Target: finish by the end of October 2026, then tear down.

| Day | Work | Done when |
| --- | --- | --- |
| 0 | Root MFA and an IAM admin user, budgets, Bedrock playground test with Nova Lite, onboarding credits, install Python 3.12, Docker, AWS CLI, Git, Node (for the CDK CLI) | A prompt returns an answer in the playground and budgets exist |
| 1 | Repo skeleton, configuration, LogRecord, plugin base, sample log generator Lambda created in the console | Logs appear in CloudWatch every 5 minutes |
| 2 | CloudWatchPlugin with pagination and checkpointing, tests using moto | Plugin returns real records since a checkpoint |
| 3 | Chunker and Titan embedder with batching and retries | A day of logs is chunked and embedded |
| 4 | FAISS store, S3 save and load, metadata file, versioned index pointer | Index round-trips through S3 |
| 5 | Retriever with filters, RAG agent through the Converse API | You can chat with your logs from a command-line script |
| 6 | Evaluation set and runner, baseline results for three Nova models | A results table exists |
| 7 | FastAPI /chat with DynamoDB memory, Streamlit UI, docker-compose | Full app runs on your laptop |
| 8 | Dockerfile, push to ECR by hand, EC2 instance role | Image sits in ECR, role is attached |
| 9 | Launch EC2 t3.micro, connect with Session Manager, run the container, lock the security group to your IP | App is live and reachable only by you |
| 10 | Log refresher Lambda with an FAISS layer, manual invoke, app reloads new index versions | New logs become searchable without a restart |
| 11 | EventBridge schedule, CloudWatch alarms, SNS email, dashboard | A forced failure sends you an email |
| 12 | Recreate everything in CDK, deploy as a fresh stack, remove the hand-built resources | cdk deploy builds it all |
| 13 | GitHub Actions: tests, image build, push to ECR through OIDC, deploy through SSM Run Command | A push to main updates the running app |
| 14 | S3 access-log plugin, end-to-end test, README, architecture diagram, demo recording | Everything is documented and recorded |
| 15 | Teardown (section 11) | Billing shows nothing running |

If you fall behind, cut the S3 plugin and the CI/CD day first. Days 1 to 9 are the core of the project.

## 10. Security checklist

- Enable MFA on the root user and use an IAM admin identity day to day.
- EC2 role: read the index prefix in one S3 bucket, invoke only the chosen Bedrock models, access one DynamoDB table, read parameters under /cloudops/.
- Refresher Lambda role: filter events on named log groups only, read and write the index prefix, invoke the Titan model only.
- No access keys on EC2 or Lambda. Never commit credentials.
- Require IMDSv2, encrypt the EBS volume, block public access on every bucket, turn on versioning for the index bucket.
- Use sample logs only. Do not index real customer or personal data.

## 11. Teardown checklist

The Free Plan ends six months after signup (around January 2027) or when credits run out. Teardown should happen right after the demo recording.

1. Run cdk destroy.
2. Empty and delete all S3 buckets, including the CDK bootstrap bucket if you are finished.
3. Delete the ECR repository and any leftover images.
4. Delete CloudWatch log groups.
5. Delete DynamoDB tables and SSM parameters.
6. Release Elastic IPs and delete EBS volumes and snapshots.
7. Search by the project tag in Tag Editor to find anything left.
8. Check Billing the next day to confirm no charges are accruing.

Keep: the GitHub repository, README, screenshots, demo recording and evaluation results.

## 12. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Bedrock model access or region mismatch | Test in the playground on Day 0, keep model ID and region in config |
| 1 GB RAM on t3.micro | No PyTorch, add swap, fall back to t3.small |
| Throttling from Bedrock | Batching and exponential backoff |
| Your home IP changes and locks you out | Update the security group, or use Session Manager port forwarding |
| A service is restricted on the Free Plan | Stay on the services listed here and do not upgrade without a budget |
| Index grows too large for Lambda | 7-day retention, flat index is fine for roughly 100,000 chunks |
| Time overrun | Cut scope from the end of the plan, never from Days 1 to 9 |

## 13. Definition of done

- A live chat that answers log questions with cited log lines.
- An evaluation table comparing three models.
- A CDK stack that deploys and destroys cleanly.
- A README with the architecture diagram, cost breakdown and lessons learned.
- A demo recording of about three minutes.

Interview talking points: why the Converse API, why an incremental index, why no NAT Gateway or load balancer, how least-privilege roles were scoped, and what the evaluation showed about each model.

## 14. Optional stretch

Only after Day 14, and only if your credit balance is healthy: deploy the same image on ECS Fargate behind an ALB for two or three days as a separate CDK stack, to see the container-orchestration approach. Expect a few dollars of credits, and destroy the stack the same day you finish.
