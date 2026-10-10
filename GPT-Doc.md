# Cloud Ops Copilot — Development Roadmap

Your project should be developed in phases, with small, testable tasks and clear completion criteria rather than trying to build the entire application at once.

Based on your Cloud Ops Copilot: Free-Tier Project Overview, the goal is to build an AWS log-analysis assistant using Python, Retrieval-Augmented Generation (RAG), Amazon Bedrock, FAISS, FastAPI, Streamlit, and AWS infrastructure services.

Cloud Ops Copilot Free-Tier Project Overview.md

The best approach is to build the working application locally first, deploy its core functionality to AWS, and then add automation, infrastructure-as-code, testing, and documentation.

## 1. Project phases at a glance

Phase 0 — Environment and AWS safety

Day 0 · Setup

Configure your development environment, AWS access, budgets, and Bedrock model access.

Phase 1 — Log ingestion

Days 1–2 · Data foundation

Create a common log format, a plugin interface, sample logs, and a CloudWatch log reader.

Phase 2 — RAG data pipeline

Days 3–4 · Chunking, embeddings, vector storage

Convert logs into searchable vectors and persist the FAISS index and metadata in S3.

Phase 3 — Retrieval and AI answers

Days 5–6 · RAG and evaluation

Retrieve relevant log records, generate evidence-based answers, and measure quality.

Phase 4 — API and chat interface

Day 7 · Application integration

Connect the RAG engine to FastAPI, DynamoDB session history, and a Streamlit UI.

Phase 5 — AWS deployment

Days 8–10 · Containers and deployment

Package the application, push it to ECR, deploy it on EC2, and automate index refresh.

Phase 6 — Monitoring and alerting

Day 11 · Operational reliability

Add CloudWatch alarms, SNS notifications, and a monitoring dashboard.

Phase 7 — Infrastructure as code and CI/CD

Days 12–13 · Reproducible delivery

Rebuild the infrastructure with AWS CDK and configure GitHub Actions using OIDC.

Phase 8 — Integration, portfolio, and teardown

Days 14–15 · Final delivery

Complete end-to-end testing, document the project, record a demo, and remove billable resources.

Important: These are the phases from your original 15-day plan, reorganized into a development workflow. The timeline is a target, not a guarantee. Each phase should pass its exit criteria before you proceed.

## 2. Detailed development tasks

Use these task IDs in your GitHub Issues or project board. Every task should have a clear deliverable and a test proving that it works.

### Phase 0 — Environment setup and AWS guardrails

Exit criteria: Safe development environment ready

| Task ID | Task                                                                      | Deliverable                      |
| ------- | ------------------------------------------------------------------------- | -------------------------------- |
| P0-01   | Install Python 3.12, Git, Docker, AWS CLI, Node.js and CDK CLI            | Tools installed and verified     |
| P0-02   | Create GitHub repository `cloudops-copilot`                               | Repository initialized           |
| P0-03   | Secure AWS root account with MFA and configure an administrative identity | Secure account access            |
| P0-04   | Configure AWS CLI and verify the selected region                          | AWS CLI identity check passes    |
| P0-05   | Create AWS Budgets alerts at $10, $25 and $50                             | Budget alerts configured         |
| P0-06   | Check account credits and test Bedrock model access in the playground     | Successful model response        |
| P0-07   | Define environment variables, project tags and configuration conventions  | Initial configuration documented |

Dependencies: None.

Test: Run Python, Git, Docker and AWS CLI successfully; make one Bedrock request; confirm that budget alerts exist.

Important: Verify the actual Bedrock model availability and pricing in your selected region. Free-tier eligibility and credits should not be assumed to cover every service or usage pattern.

### Phase 1 — Repository foundation and log ingestion

Exit criteria: Application can read sample and CloudWatch logs

| Task ID | Task                                                       | Deliverable                      |
| ------- | ---------------------------------------------------------- | -------------------------------- |
| P1-01   | Create the project directory structure                     | Initial repository skeleton      |
| P1-02   | Define the `LogRecord` data model                          | Consistent normalized log format |
| P1-03   | Implement the abstract `LogPlugin` interface               | Standard plugin contract         |
| P1-04   | Build a sample Lambda log generator                        | Synthetic logs in CloudWatch     |
| P1-05   | Create `CloudWatchPlugin`                                  | CloudWatch log reader            |
| P1-06   | Implement time-window queries and pagination               | Complete retrieval across pages  |
| P1-07   | Add checkpoint handling for incremental ingestion          | Only new records are processed   |
| P1-08   | Write unit tests using `pytest` and `moto` where supported | Tested ingestion logic           |

The core data model should contain:

* `id`

* `timestamp`

* `source`

* `service`

* `level`

* `message`

* `attributes`

Example record:

Python

Run

```
{
    "id": "checkout-001",
    "timestamp": "2026-10-09T14:00:00Z",
    "source": "cloudwatch",
    "service": "checkout-lambda",
    "level": "ERROR",
    "message": "Database connection timed out",
    "attributes": {"request_id": "abc123"}
}
```

Dependencies: Phase 0.

Test: Generate sample logs, retrieve them through the plugin, and verify that timestamps, IDs and pagination work correctly.

### Phase 2 — Chunking, embeddings and vector storage

Exit criteria: Logs can be indexed and reloaded from S3

| Task ID | Task                                                              | Deliverable                            |
| ------- | ----------------------------------------------------------------- | -------------------------------------- |
| P2-01   | Implement log normalization and deduplication                     | Clean input records                    |
| P2-02   | Implement `core/chunker.py`                                       | Chunks of approximately 300–500 tokens |
| P2-03   | Preserve request IDs, timestamps and service metadata             | Traceable chunks                       |
| P2-04   | Implement the Bedrock Titan Text Embeddings v2 client             | Embedding generation                   |
| P2-05   | Add batching, throttling retries and error handling               | Resilient embedding pipeline           |
| P2-06   | Implement normalized vectors and a FAISS flat inner-product index | Similarity search index                |
| P2-07   | Store chunk text and metadata as JSON                             | Metadata persistence                   |
| P2-08   | Save the index and metadata to S3                                 | Persistent index artifacts             |
| P2-09   | Implement versioned index paths and a latest-pointer file         | Reliable index version selection       |
| P2-10   | Test saving and reloading the complete index                      | Successful round-trip test             |

Dependencies: Phase 1.

Test: Ingest a known set of logs, embed them, upload the index to S3, reload it, and retrieve the expected records.

Design rule: Keep vector IDs aligned with metadata IDs. Rebuilding or appending an index must not silently corrupt that mapping.

### Phase 3 — Retrieval, RAG agent and evaluation

Exit criteria: Questions receive evidence-backed answers

| Task ID | Task                                                          | Deliverable                    |
| ------- | ------------------------------------------------------------- | ------------------------------ |
| P3-01   | Implement `agent/retriever.py`                                | Top-8 relevant chunk retrieval |
| P3-02   | Add service, severity and time filters                        | Filtered retrieval             |
| P3-03   | Implement the Bedrock Converse API client                     | Configurable answer generation |
| P3-04   | Build the RAG prompt with evidence-only instructions          | Grounded response behavior     |
| P3-05   | Include log IDs and timestamps in citations                   | Traceable answers              |
| P3-06   | Handle missing evidence and model errors                      | Safe fallback responses        |
| P3-07   | Create 25 evaluation questions with known answers             | Evaluation dataset             |
| P3-08   | Implement recall-at-8 and answer/citation checks              | Evaluation runner              |
| P3-09   | Compare Nova Micro, Nova Lite and Nova 2 Lite where available | Model comparison results       |

Dependencies: Phase 2.

Test: Ask why a simulated checkout Lambda failed. The assistant should identify the timeout only if the retrieved logs support it, cite the relevant log IDs, and acknowledge missing evidence when necessary.

Example target interaction:

USER

Why did checkout fail around 2 PM?

CLOUD OPS COPILOT

The available logs indicate that checkout failed because a database connection timed out.

Evidence

* Time: 14:00 UTC

* Service: checkout-lambda

* Severity: ERROR

* Log ID: `checkout-001`

The logs establish the timeout, but additional database telemetry would be needed to determine its underlying cause.

Do not move to UI development until retrieval and citations work reliably from a command-line script.

### Phase 4 — API, session memory and user interface

Exit criteria: Complete local chat application

| Task ID | Task                                              | Deliverable                      |
| ------- | ------------------------------------------------- | -------------------------------- |
| P4-01   | Implement `api/server.py` with FastAPI            | Application server               |
| P4-02   | Create `GET /health`                              | Health-check endpoint            |
| P4-03   | Create `POST /chat`                               | Chat API                         |
| P4-04   | Validate request and response schemas             | Predictable API contract         |
| P4-05   | Implement DynamoDB session history                | Persistent conversation history  |
| P4-06   | Restrict memory to the last six turns per session | Bounded conversation context     |
| P4-07   | Build `ui/app.py` using Streamlit                 | Chat interface                   |
| P4-08   | Connect Streamlit to FastAPI                      | End-to-end local interaction     |
| P4-09   | Configure Docker Compose for local development    | Reproducible application startup |
| P4-10   | Add integration tests for chat, errors and memory | Verified app behavior            |

Dependencies: Phase 3.

Test: Start the app locally and ask a question through Streamlit. Verify that the API returns citations and that follow-up questions can use the session history.

### Phase 5 — Containerization and first AWS deployment

Exit criteria: Private, working cloud deployment

| Task ID | Task                                                            | Deliverable                  |
| ------- | --------------------------------------------------------------- | ---------------------------- |
| P5-01   | Write the production Dockerfile                                 | Container image              |
| P5-02   | Test memory usage and startup behavior                          | Container validated locally  |
| P5-03   | Create a private ECR repository                                 | Image registry               |
| P5-04   | Build and push the image to ECR                                 | Published image              |
| P5-05   | Create a least-privilege EC2 instance role                      | Scoped AWS permissions       |
| P5-06   | Launch a small EC2 instance                                     | Compute environment          |
| P5-07   | Configure SSM Session Manager                                   | Shell access without SSH     |
| P5-08   | Configure S3, Bedrock, DynamoDB and Parameter Store permissions | Runtime access               |
| P5-09   | Restrict application ingress to your current public IP          | Limited network access       |
| P5-10   | Start the container and verify `/health` and `/chat`            | Working deployed application |

Dependencies: Phase 4.

Test: Open the application from your permitted IP, ask a log question, and verify that the running container can access its AWS dependencies.

For the first version, keep the EC2 instance simple. Do not add a load balancer, NAT Gateway or managed search service.

### Phase 6 — Automated ingestion and monitoring

Exit criteria: New logs become searchable automatically

| Task ID | Task                                                        | Deliverable                      |
| ------- | ----------------------------------------------------------- | -------------------------------- |
| P6-01   | Implement the log-refresher Lambda                          | Incremental index builder        |
| P6-02   | Read new logs after the saved checkpoint                    | Incremental ingestion            |
| P6-03   | Reuse embedding and vector-store logic                      | Consistent index updates         |
| P6-04   | Add an S3 FAISS Lambda layer or compatible package strategy | Deployable refresher             |
| P6-05   | Publish new index versions and update the latest pointer    | Versioned refresh                |
| P6-06   | Implement application index reload logic                    | New index loaded without restart |
| P6-07   | Schedule the refresher every 30 minutes with EventBridge    | Scheduled refresh                |
| P6-08   | Configure CloudWatch alarms and an SNS email topic          | Failure notifications            |
| P6-09   | Create a CloudWatch dashboard                               | Operational visibility           |
| P6-10   | Test a forced failure and a successful refresh              | Verified recovery and alerting   |

Dependencies: Phase 5.

Test: Generate new logs, trigger the refresh, and confirm that the new records can be queried without restarting the app.

Implementation consideration: FAISS binary compatibility, Lambda package size, execution time and memory are key risks. Test the refresher in the actual Lambda environment before relying on it.

### Phase 7 — Infrastructure as code and CI/CD

Exit criteria: Infrastructure is reproducible

| Task ID | Task                                                                | Deliverable                         |
| ------- | ------------------------------------------------------------------- | ----------------------------------- |
| P7-01   | Define a Python CDK application                                     | Infrastructure project              |
| P7-02   | Create the S3 bucket, ECR repository, DynamoDB table and parameters | Data and configuration resources    |
| P7-03   | Define IAM roles and policies                                       | Repeatable permissions              |
| P7-04   | Define Lambda functions, schedules and alarms                       | Automated infrastructure            |
| P7-05   | Define EC2, security group and instance profile                     | Compute stack                       |
| P7-06   | Configure tags, encryption and security defaults                    | Consistent resource controls        |
| P7-07   | Run CDK synthesis and review the generated template                 | Validated infrastructure definition |
| P7-08   | Deploy a clean stack and verify its resources                       | Reproducible deployment             |
| P7-09   | Remove duplicate hand-built resources safely                        | Single managed environment          |
| P7-10   | Configure GitHub Actions for tests and Docker builds                | CI pipeline                         |
| P7-11   | Configure GitHub OIDC federation with AWS                           | Short-lived deployment credentials  |
| P7-12   | Automate ECR publishing and EC2 deployment through SSM              | Continuous delivery                 |

Dependencies: Phase 6 for the full infrastructure recreation; basic CDK learning can begin earlier.

Test: A clean deployment should work from CDK, and a push to the main branch should run tests, publish the image and update the running application.

Treat this as a migration, not a second parallel production environment. Inventory the resources before replacing manually created infrastructure.

### Phase 8 — Final integration, optional plugin and project closure

Exit criteria: Portfolio-ready project and clean AWS account

| Task ID | Task                                                       | Deliverable           |
| ------- | ---------------------------------------------------------- | --------------------- |
| P8-01   | Run the complete ingestion-to-answer test                  | End-to-end validation |
| P8-02   | Add `S3AccessLogPlugin` if time permits                    | Second log source     |
| P8-03   | Run the 25-question evaluation suite                       | Final metrics         |
| P8-04   | Document architecture and data flow                        | Architecture diagram  |
| P8-05   | Document cost estimates, setup and teardown                | Complete README       |
| P8-06   | Record a three-minute demonstration                        | Demo video            |
| P8-07   | Review IAM permissions, sample data and exposed ports      | Security review       |
| P8-08   | Run `cdk destroy` and remove remaining resources           | AWS teardown          |
| P8-09   | Check S3, ECR, EBS, IP addresses, logs and other leftovers | Resource cleanup      |
| P8-10   | Verify billing and retain portfolio artifacts              | Final handover        |

Dependencies: Phases 3–7, with the optional S3 plugin dependent on the core pipeline being stable.

## 3. Recommended repository structure

Create this structure in Phase 1 and add files as their tasks begin.

cloudops-copilot/

plugins/

`base.py`, `cloudwatch_plugin.py`, `s3_access_plugin.py`

core/

`models.py`, `chunker.py`, `embedder.py`, `vector_store.py`

agent/

`retriever.py`, `rag_agent.py`, `memory.py`

api/ and ui/

FastAPI server and Streamlit application

lambdas/

`log_generator/`, `log_refresher/`

infra/

Python AWS CDK application

eval/ and tests/

Evaluation questions, metrics and unit/integration tests

Root configuration

`Dockerfile`, `docker-compose.yml`, `pyproject.toml`, `.gitignore`, `.env.example`, `README.md`

Keep AWS credentials and actual `.env` files out of Git. Store non-secret configuration such as model IDs and bucket names in configuration files or Parameter Store as appropriate.

## 4. Task dependencies

This is the recommended build order. The main pipeline must work before you invest time in deployment automation.

Diagram options

![](data\:image/svg+xml;utf8,%3Csvg%20id%3D%22mermaid-_r_bh_%22%20width%3D%22493.4672546386719%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20class%3D%22flowchart%22%20height%3D%22920.800048828125%22%20viewBox%3D%224%204.000003814697266%20493.4672546386719%20920.800048828125%22%20role%3D%22graphics-document%20document%22%20aria-roledescription%3D%22flowchart-v2%22%3E%3Cstyle%3E%23mermaid-_r_bh_%7Bfont-family%3A%22-apple-system%22%2C%22BlinkMacSystemFont%22%2C%22Segoe%20UI%22%2C%22Roboto%22%2C%22Oxygen%22%2C%22Ubuntu%22%2C%22Cantarell%22%2C%22Helvetica%20Neue%22%2C%22Arial%22%2C%22sans-serif%22%3Bfont-size%3A14px%3Bfill%3Argb\(255%2C%20255%2C%20255\)%3B%7D%40keyframes%20edge-animation-frame%7Bfrom%7Bstroke-dashoffset%3A0%3B%7D%7D%40keyframes%20dash%7Bto%7Bstroke-dashoffset%3A0%3B%7D%7D%23mermaid-_r_bh_%20.edge-animation-slow%7Bstroke-dasharray%3A9%2C5!important%3Bstroke-dashoffset%3A900%3Banimation%3Adash%2050s%20linear%20infinite%3Bstroke-linecap%3Around%3B%7D%23mermaid-_r_bh_%20.edge-animation-fast%7Bstroke-dasharray%3A9%2C5!important%3Bstroke-dashoffset%3A900%3Banimation%3Adash%2020s%20linear%20infinite%3Bstroke-linecap%3Around%3B%7D%23mermaid-_r_bh_%20.error-icon%7Bfill%3Argb\(33%2C%2033%2C%2033\)%3B%7D%23mermaid-_r_bh_%20.error-text%7Bfill%3Argb\(255%2C%20255%2C%20255\)%3Bstroke%3Argb\(255%2C%20255%2C%20255\)%3B%7D%23mermaid-_r_bh_%20.edge-thickness-normal%7Bstroke-width%3A1px%3B%7D%23mermaid-_r_bh_%20.edge-thickness-thick%7Bstroke-width%3A3.5px%3B%7D%23mermaid-_r_bh_%20.edge-pattern-solid%7Bstroke-dasharray%3A0%3B%7D%23mermaid-_r_bh_%20.edge-thickness-invisible%7Bstroke-width%3A0%3Bfill%3Anone%3B%7D%23mermaid-_r_bh_%20.edge-pattern-dashed%7Bstroke-dasharray%3A3%3B%7D%23mermaid-_r_bh_%20.edge-pattern-dotted%7Bstroke-dasharray%3A2%3B%7D%23mermaid-_r_bh_%20.marker%7Bfill%3Argb\(205%2C%20205%2C%20205\)%3Bstroke%3Argb\(205%2C%20205%2C%20205\)%3B%7D%23mermaid-_r_bh_%20.marker.cross%7Bstroke%3Argb\(205%2C%20205%2C%20205\)%3B%7D%23mermaid-_r_bh_%20svg%7Bfont-family%3A%22-apple-system%22%2C%22BlinkMacSystemFont%22%2C%22Segoe%20UI%22%2C%22Roboto%22%2C%22Oxygen%22%2C%22Ubuntu%22%2C%22Cantarell%22%2C%22Helvetica%20Neue%22%2C%22Arial%22%2C%22sans-serif%22%3Bfont-size%3A14px%3B%7D%23mermaid-_r_bh_%20p%7Bmargin%3A0%3B%7D%23mermaid-_r_bh_%20.label%7Bfont-family%3A%22-apple-system%22%2C%22BlinkMacSystemFont%22%2C%22Segoe%20UI%22%2C%22Roboto%22%2C%22Oxygen%22%2C%22Ubuntu%22%2C%22Cantarell%22%2C%22Helvetica%20Neue%22%2C%22Arial%22%2C%22sans-serif%22%3Bcolor%3Argb\(255%2C%20255%2C%20255\)%3B%7D%23mermaid-_r_bh_%20.cluster-label%20text%7Bfill%3Argb\(255%2C%20255%2C%20255\)%3B%7D%23mermaid-_r_bh_%20.cluster-label%20span%7Bcolor%3Argb\(255%2C%20255%2C%20255\)%3B%7D%23mermaid-_r_bh_%20.cluster-label%20span%20p%7Bbackground-color%3Atransparent%3B%7D%23mermaid-_r_bh_%20.label%20text%2C%23mermaid-_r_bh_%20span%7Bfill%3Argb\(255%2C%20255%2C%20255\)%3Bcolor%3Argb\(255%2C%20255%2C%20255\)%3B%7D%23mermaid-_r_bh_%20.node%20rect%2C%23mermaid-_r_bh_%20.node%20circle%2C%23mermaid-_r_bh_%20.node%20ellipse%2C%23mermaid-_r_bh_%20.node%20polygon%2C%23mermaid-_r_bh_%20.node%20path%7Bfill%3Argb\(9%2C%2023%2C%2044\)%3Bstroke%3Argb\(31%2C%2078%2C%20148\)%3Bstroke-width%3A1px%3B%7D%23mermaid-_r_bh_%20.rough-node%20.label%20text%2C%23mermaid-_r_bh_%20.node%20.label%20text%2C%23mermaid-_r_bh_%20.image-shape%20.label%2C%23mermaid-_r_bh_%20.icon-shape%20.label%7Btext-anchor%3Amiddle%3B%7D%23mermaid-_r_bh_%20.node%20.katex%20path%7Bfill%3A%23000%3Bstroke%3A%23000%3Bstroke-width%3A1px%3B%7D%23mermaid-_r_bh_%20.rough-node%20.label%2C%23mermaid-_r_bh_%20.node%20.label%2C%23mermaid-_r_bh_%20.image-shape%20.label%2C%23mermaid-_r_bh_%20.icon-shape%20.label%7Btext-align%3Acenter%3B%7D%23mermaid-_r_bh_%20.node.clickable%7Bcursor%3Apointer%3B%7D%23mermaid-_r_bh_%20.root%20.anchor%20path%7Bfill%3Argb\(205%2C%20205%2C%20205\)!important%3Bstroke-width%3A0%3Bstroke%3Argb\(205%2C%20205%2C%20205\)%3B%7D%23mermaid-_r_bh_%20.arrowheadPath%7Bfill%3Argb\(205%2C%20205%2C%20205\)%3B%7D%23mermaid-_r_bh_%20.edgePath%20.path%7Bstroke%3Argb\(205%2C%20205%2C%20205\)%3Bstroke-width%3A2.0px%3B%7D%23mermaid-_r_bh_%20.flowchart-link%7Bstroke%3Argb\(205%2C%20205%2C%20205\)%3Bfill%3Anone%3B%7D%23mermaid-_r_bh_%20.edgeLabel%7Bbackground-color%3Argb\(0%2C%200%2C%200\)%3Btext-align%3Acenter%3B%7D%23mermaid-_r_bh_%20.edgeLabel%20p%7Bbackground-color%3Argb\(0%2C%200%2C%200\)%3B%7D%23mermaid-_r_bh_%20.edgeLabel%20rect%7Bopacity%3A0.5%3Bbackground-color%3Argb\(0%2C%200%2C%200\)%3Bfill%3Argb\(0%2C%200%2C%200\)%3B%7D%23mermaid-_r_bh_%20.labelBkg%7Bbackground-color%3Argba\(0%2C%200%2C%200%2C%200.5\)%3B%7D%23mermaid-_r_bh_%20.cluster%20rect%7Bfill%3Argb\(33%2C%2033%2C%2033\)%3Bstroke%3Argba\(255%2C%20255%2C%20255%2C%200.05\)%3Bstroke-width%3A1px%3B%7D%23mermaid-_r_bh_%20.cluster%20text%7Bfill%3Argb\(255%2C%20255%2C%20255\)%3B%7D%23mermaid-_r_bh_%20.cluster%20span%7Bcolor%3Argb\(255%2C%20255%2C%20255\)%3B%7D%23mermaid-_r_bh_%20div.mermaidTooltip%7Bposition%3Aabsolute%3Btext-align%3Acenter%3Bmax-width%3A200px%3Bpadding%3A2px%3Bfont-family%3A%22-apple-system%22%2C%22BlinkMacSystemFont%22%2C%22Segoe%20UI%22%2C%22Roboto%22%2C%22Oxygen%22%2C%22Ubuntu%22%2C%22Cantarell%22%2C%22Helvetica%20Neue%22%2C%22Arial%22%2C%22sans-serif%22%3Bfont-size%3A12px%3Bbackground%3Argb\(33%2C%2033%2C%2033\)%3Bborder%3A1px%20solid%20rgba\(255%2C%20255%2C%20255%2C%200.05\)%3Bborder-radius%3A2px%3Bpointer-events%3Anone%3Bz-index%3A100%3B%7D%23mermaid-_r_bh_%20.flowchartTitleText%7Btext-anchor%3Amiddle%3Bfont-size%3A18px%3Bfill%3Argb\(255%2C%20255%2C%20255\)%3B%7D%23mermaid-_r_bh_%20rect.text%7Bfill%3Anone%3Bstroke-width%3A0%3B%7D%23mermaid-_r_bh_%20.icon-shape%2C%23mermaid-_r_bh_%20.image-shape%7Bbackground-color%3Argb\(0%2C%200%2C%200\)%3Btext-align%3Acenter%3B%7D%23mermaid-_r_bh_%20.icon-shape%20p%2C%23mermaid-_r_bh_%20.image-shape%20p%7Bbackground-color%3Argb\(0%2C%200%2C%200\)%3Bpadding%3A2px%3B%7D%23mermaid-_r_bh_%20.icon-shape%20rect%2C%23mermaid-_r_bh_%20.image-shape%20rect%7Bopacity%3A0.5%3Bbackground-color%3Argb\(0%2C%200%2C%200\)%3Bfill%3Argb\(0%2C%200%2C%200\)%3B%7D%23mermaid-_r_bh_%20.label-icon%7Bdisplay%3Ainline-block%3Bheight%3A1em%3Boverflow%3Avisible%3Bvertical-align%3A-0.125em%3B%7D%23mermaid-_r_bh_%20.node%20.label-icon%20path%7Bfill%3AcurrentColor%3Bstroke%3Arevert%3Bstroke-width%3Arevert%3B%7D%23mermaid-_r_bh_%20.node%20text%7Bfont-size%3A16px%3Bfont-weight%3A600%3Bletter-spacing%3A-0.32px%3Bfill%3A%2399ceff%3B%7D%23mermaid-_r_bh_%20.edgeLabels%20text%7Bfont-size%3A13px%3Bfont-weight%3A600%3Bletter-spacing%3A-0.08px%3Bfill%3A%2399ceff%3B%7D%23mermaid-_r_bh_%20.node%20tspan%5Bfont-weight%3D%22normal%22%5D%2C%23mermaid-_r_bh_%20.edgeLabels%20tspan%5Bfont-weight%3D%22normal%22%5D%7Bfont-weight%3A600%3B%7D%23mermaid-_r_bh_%20.edgeLabel%20.label%20rect%7Bopacity%3A1%3Brx%3A13px%3Bry%3A13px%3Bfill%3A%23000e1a%3Bstroke%3Argb\(26%2C%2062%2C%2095\)%3Bstroke-width%3A1px%3B%7D%23mermaid-_r_bh_%20.node%20rect%2C%23mermaid-_r_bh_%20.node%20circle%2C%23mermaid-_r_bh_%20.node%20ellipse%2C%23mermaid-_r_bh_%20.node%20polygon%2C%23mermaid-_r_bh_%20.node%20path%7Bfill%3Argb\(0%2C%2040%2C%2077\)%3Bstroke%3Argba\(255%2C%20255%2C%20255%2C%200.1\)%3Bstroke-width%3A1px%3B%7D%23mermaid-_r_bh_%20.node%20rect%7Brx%3A16px%3Bry%3A16px%3B%7D%23mermaid-_r_bh_%20.node.mermaid-decision%20.label-container%7Bfill%3A%23000e1a%3Bstroke%3Argb\(26%2C%2062%2C%2095\)%3Bstroke-dasharray%3A2%202%3B%7D%23mermaid-_r_bh_%20.edgePaths%20.flowchart-link%7Bstroke%3Argb\(26%2C%2062%2C%2095\)%3Bstroke-width%3A1px%3Bstroke-linecap%3Around%3Bstroke-linejoin%3Around%3B%7D%23mermaid-_r_bh_%20.marker%7Bfill%3Argb\(26%2C%2062%2C%2095\)%3Bstroke%3Argb\(26%2C%2062%2C%2095\)%3B%7D%23mermaid-_r_bh_%20.node%7Bcolor-scheme%3Adark%3B%7D%23mermaid-_r_bh_%20%3Aroot%7B--mermaid-font-family%3A%22-apple-system%22%2C%22BlinkMacSystemFont%22%2C%22Segoe%20UI%22%2C%22Roboto%22%2C%22Oxygen%22%2C%22Ubuntu%22%2C%22Cantarell%22%2C%22Helvetica%20Neue%22%2C%22Arial%22%2C%22sans-serif%22%3B%7D%3C%2Fstyle%3E%3Cg%3E%3Cmarker%20id%3D%22mermaid-_r_bh__flowchart-v2-pointEnd%22%20class%3D%22marker%20flowchart-v2%22%20viewBox%3D%22-5%20-5%2010%2010%22%20refX%3D%220%22%20refY%3D%220%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2210%22%20markerHeight%3D%2210%22%20orient%3D%22auto%22%3E%3Cpath%20d%3D%22M%200%200%20L%204%200%20M%200.8180194846605362%20-3.181980515339464%20L%204%200%20L%200.8180194846605362%203.181980515339464%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%201%3B%20stroke-dasharray%3A%20none%3B%20fill%3A%20none%3B%20stroke-linecap%3A%20round%3B%20stroke-linejoin%3A%20round%3B%22%3E%3C%2Fpath%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_bh__flowchart-v2-pointStart%22%20class%3D%22marker%20flowchart-v2%22%20viewBox%3D%22-5%20-5%2010%2010%22%20refX%3D%220%22%20refY%3D%220%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2210%22%20markerHeight%3D%2210%22%20orient%3D%22auto%22%3E%3Cpath%20d%3D%22M%200%200%20L%20-4%200%20M%20-0.8180194846605362%20-3.181980515339464%20L%20-4%200%20L%20-0.8180194846605362%203.181980515339464%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%201%3B%20stroke-dasharray%3A%20none%3B%20fill%3A%20none%3B%20stroke-linecap%3A%20round%3B%20stroke-linejoin%3A%20round%3B%22%3E%3C%2Fpath%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_bh__flowchart-v2-circleEnd%22%20class%3D%22marker%20flowchart-v2%22%20viewBox%3D%220%200%2010%2010%22%20refX%3D%2211%22%20refY%3D%225%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2211%22%20markerHeight%3D%2211%22%20orient%3D%22auto%22%3E%3Ccircle%20cx%3D%225%22%20cy%3D%225%22%20r%3D%225%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%201%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fcircle%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_bh__flowchart-v2-circleStart%22%20class%3D%22marker%20flowchart-v2%22%20viewBox%3D%220%200%2010%2010%22%20refX%3D%22-1%22%20refY%3D%225%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2211%22%20markerHeight%3D%2211%22%20orient%3D%22auto%22%3E%3Ccircle%20cx%3D%225%22%20cy%3D%225%22%20r%3D%225%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%201%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fcircle%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_bh__flowchart-v2-crossEnd%22%20class%3D%22marker%20cross%20flowchart-v2%22%20viewBox%3D%220%200%2011%2011%22%20refX%3D%2212%22%20refY%3D%225.2%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2211%22%20markerHeight%3D%2211%22%20orient%3D%22auto%22%3E%3Cpath%20d%3D%22M%201%2C1%20l%209%2C9%20M%2010%2C1%20l%20-9%2C9%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%202%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fpath%3E%3C%2Fmarker%3E%3Cmarker%20id%3D%22mermaid-_r_bh__flowchart-v2-crossStart%22%20class%3D%22marker%20cross%20flowchart-v2%22%20viewBox%3D%220%200%2011%2011%22%20refX%3D%22-1%22%20refY%3D%225.2%22%20markerUnits%3D%22userSpaceOnUse%22%20markerWidth%3D%2211%22%20markerHeight%3D%2211%22%20orient%3D%22auto%22%3E%3Cpath%20d%3D%22M%201%2C1%20l%209%2C9%20M%2010%2C1%20l%20-9%2C9%22%20class%3D%22arrowMarkerPath%22%20style%3D%22stroke-width%3A%202%3B%20stroke-dasharray%3A%201%2C%200%3B%22%3E%3C%2Fpath%3E%3C%2Fmarker%3E%3C%2Fg%3E%3Cg%20class%3D%22subgraphs%22%3E%3C%2Fg%3E%3Cg%20class%3D%22nodes%22%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-A-0%22%20transform%3D%22translate\(182.92319742838544%2C%2047.599998474121094\)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-126.20000457763672%22%20y%3D%22-35.599998474121094%22%20width%3D%22252.40000915527344%22%20height%3D%2271.19999694824219%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate\(0%2C%20-19.599998474121094\)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EPhase%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%200%3A%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Environment%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20and%3C%2Ftspan%3E%3C%2Ftspan%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%221em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3Esafety%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-B-1%22%20transform%3D%22translate\(182.92319742838544%2C%20153.1999969482422\)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-112.65625%22%20y%3D%22-30%22%20width%3D%22225.3125%22%20height%3D%2260%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate\(0%2C%20-10.800000190734863\)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EPhase%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%201%3A%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Log%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20ingestion%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-C-3%22%20transform%3D%22translate\(182.92319742838544%2C%20258.7999954223633\)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-115.23125457763672%22%20y%3D%22-35.599998474121094%22%20width%3D%22230.46250915527344%22%20height%3D%2271.19999694824219%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate\(0%2C%20-19.599998474121094\)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EPhase%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%202%3A%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Chunking%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20and%3C%2Ftspan%3E%3C%2Ftspan%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%221em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EFAISS%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-D-5%22%20transform%3D%22translate\(182.92319742838544%2C%20364.3999938964844\)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-129.13750457763672%22%20y%3D%22-30%22%20width%3D%22258.27500915527344%22%20height%3D%2260%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate\(0%2C%20-10.800000190734863\)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EPhase%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%203%3A%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Retrieval%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20and%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20RAG%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-E-7%22%20transform%3D%22translate\(139.8773651123047%2C%20464.3999938964844\)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-103.5250015258789%22%20y%3D%22-30%22%20width%3D%22207.0500030517578%22%20height%3D%2260%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate\(0%2C%20-10.800000190734863\)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EPhase%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%204%3A%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20API%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20and%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20UI%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-F-9%22%20transform%3D%22translate\(139.8773651123047%2C%20564.3999938964844\)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-127.87737274169922%22%20y%3D%22-30%22%20width%3D%22255.75474548339844%22%20height%3D%2260%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate\(0%2C%20-10.800000190734863\)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EPhase%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%205%3A%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20AWS%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20deployment%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-G-11%22%20transform%3D%22translate\(139.8773651123047%2C%20669.9999923706055\)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-107.70000457763672%22%20y%3D%22-35.599998474121094%22%20width%3D%22215.40000915527344%22%20height%3D%2271.19999694824219%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate\(0%2C%20-19.599998474121094\)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EPhase%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%206%3A%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Refresh%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20and%3C%2Ftspan%3E%3C%2Ftspan%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%221em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3Emonitoring%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-H-13%22%20transform%3D%22translate\(139.8773651123047%2C%20775.5999908447266\)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-119.31486511230469%22%20y%3D%22-30%22%20width%3D%22238.62973022460938%22%20height%3D%2260%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate\(0%2C%20-10.800000190734863\)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EPhase%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%207%3A%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20CDK%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20and%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20CI%2FCD%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-I-15%22%20transform%3D%22translate\(181.19403076171875%2C%20881.1999893188477\)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-123.95000457763672%22%20y%3D%22-35.599998474121094%22%20width%3D%22247.90000915527344%22%20height%3D%2271.19999694824219%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate\(0%2C%20-19.599998474121094\)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EPhase%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%208%3A%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20Final%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20testing%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20and%3C%2Ftspan%3E%3C%2Ftspan%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%221em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3Eteardown%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22node%20default%22%20id%3D%22flowchart-J-17%22%20transform%3D%22translate\(398.6109924316406%2C%20564.3999938964844\)%22%3E%3Crect%20class%3D%22basic%20label-container%22%20style%3D%22%22%20x%3D%22-90.85626220703125%22%20y%3D%22-30%22%20width%3D%22181.7125244140625%22%20height%3D%2260%22%3E%3C%2Frect%3E%3Cg%20class%3D%22label%22%20style%3D%22%22%20transform%3D%22translate\(0%2C%20-10.800000190734863\)%22%3E%3Crect%3E%3C%2Frect%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3Ctext%20y%3D%22-10.1%22%20style%3D%22%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3EEvaluation%3C%2Ftspan%3E%3Ctspan%20font-style%3D%22normal%22%20class%3D%22text-inner-tspan%22%20font-weight%3D%22normal%22%3E%20suite%3C%2Ftspan%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edges%20edgePaths%22%3E%3Cpath%20d%3D%22M182.92319742838544%2C83.19999694824219L182.92319742838544%2C111.19999694824219%22%20id%3D%22L_A_B_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_A_B_0%22%20data-points%3D%22W3sieCI6MTgyLjkyMzE5NzQyODM4NTQ0LCJ5Ijo4My4xOTk5OTY5NDgyNDIxOX0seyJ4IjoxODIuOTIzMTk3NDI4Mzg1NDQsInkiOjExNS4xOTk5OTY5NDgyNDIxOX1d%22%20marker-end%3D%22url\(%23mermaid-_r_bh__flowchart-v2-pointEnd\)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M182.92319742838544%2C183.1999969482422L182.92319742838544%2C211.1999969482422%22%20id%3D%22L_B_C_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_B_C_0%22%20data-points%3D%22W3sieCI6MTgyLjkyMzE5NzQyODM4NTQ0LCJ5IjoxODMuMTk5OTk2OTQ4MjQyMn0seyJ4IjoxODIuOTIzMTk3NDI4Mzg1NDQsInkiOjIxNS4xOTk5OTY5NDgyNDIyfV0%3D%22%20marker-end%3D%22url\(%23mermaid-_r_bh__flowchart-v2-pointEnd\)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M182.92319742838544%2C294.3999938964844L182.92319742838544%2C322.3999938964844%22%20id%3D%22L_C_D_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_C_D_0%22%20data-points%3D%22W3sieCI6MTgyLjkyMzE5NzQyODM4NTQ0LCJ5IjoyOTQuMzk5OTkzODk2NDg0NH0seyJ4IjoxODIuOTIzMTk3NDI4Mzg1NDQsInkiOjMyNi4zOTk5OTM4OTY0ODQ0fV0%3D%22%20marker-end%3D%22url\(%23mermaid-_r_bh__flowchart-v2-pointEnd\)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M139.8773651123047%2C394.3999938964844L139.8773651123047%2C422.3999938964844%22%20id%3D%22L_D_E_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_D_E_0%22%20data-points%3D%22W3sieCI6MTM5Ljg3NzM2NTExMjMwNDcsInkiOjM5NC4zOTk5OTM4OTY0ODQ0fSx7IngiOjEzOS44NzczNjUxMTIzMDQ3LCJ5Ijo0MjYuMzk5OTkzODk2NDg0NH1d%22%20marker-end%3D%22url\(%23mermaid-_r_bh__flowchart-v2-pointEnd\)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M139.8773651123047%2C494.3999938964844L139.8773651123047%2C522.3999938964844%22%20id%3D%22L_E_F_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_E_F_0%22%20data-points%3D%22W3sieCI6MTM5Ljg3NzM2NTExMjMwNDcsInkiOjQ5NC4zOTk5OTM4OTY0ODQ0fSx7IngiOjEzOS44NzczNjUxMTIzMDQ3LCJ5Ijo1MjYuMzk5OTkzODk2NDg0NH1d%22%20marker-end%3D%22url\(%23mermaid-_r_bh__flowchart-v2-pointEnd\)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M139.8773651123047%2C594.3999938964844L139.8773651123047%2C622.3999938964844%22%20id%3D%22L_F_G_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_F_G_0%22%20data-points%3D%22W3sieCI6MTM5Ljg3NzM2NTExMjMwNDcsInkiOjU5NC4zOTk5OTM4OTY0ODQ0fSx7IngiOjEzOS44NzczNjUxMTIzMDQ3LCJ5Ijo2MjYuMzk5OTkzODk2NDg0NH1d%22%20marker-end%3D%22url\(%23mermaid-_r_bh__flowchart-v2-pointEnd\)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M139.8773651123047%2C705.5999908447266L139.8773651123047%2C733.5999908447266%22%20id%3D%22L_G_H_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_G_H_0%22%20data-points%3D%22W3sieCI6MTM5Ljg3NzM2NTExMjMwNDcsInkiOjcwNS41OTk5OTA4NDQ3MjY2fSx7IngiOjEzOS44NzczNjUxMTIzMDQ3LCJ5Ijo3MzcuNTk5OTkwODQ0NzI2Nn1d%22%20marker-end%3D%22url\(%23mermaid-_r_bh__flowchart-v2-pointEnd\)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M139.8773651123047%2C805.5999908447266L139.8773651123047%2C833.5999908447266%22%20id%3D%22L_H_I_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_H_I_0%22%20data-points%3D%22W3sieCI6MTM5Ljg3NzM2NTExMjMwNDcsInkiOjgwNS41OTk5OTA4NDQ3MjY2fSx7IngiOjEzOS44NzczNjUxMTIzMDQ3LCJ5Ijo4MzcuNTk5OTkwODQ0NzI2Nn1d%22%20marker-end%3D%22url\(%23mermaid-_r_bh__flowchart-v2-pointEnd\)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M225.9690297444661%2C394.3999938964844L225.96902974446613%2C407.3289260846189Q225.96902974446613%2C414.3999938964844%20233.0400975563316%2C414.3999938964844L391.828036406346%2C414.3999938964844Q393.6109924316406%2C414.3999938964844%20395.02520599401373%2C415.48578033411127L395.02520599401373%2C415.48578033411127Q396.43941955638684%2C416.57156677173816%20397.52520599401373%2C417.98578033411127L397.52520599401373%2C417.98578033411127Q398.6109924316406%2C419.3999938964844%20398.6109924316406%2C421.182949921779L398.6109924316406%2C464.3999938964844L398.6109924316406%2C522.3999938964844%22%20id%3D%22L_D_J_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_D_J_0%22%20data-points%3D%22W3sieCI6MjI1Ljk2OTAyOTc0NDQ2NjEsInkiOjM5NC4zOTk5OTM4OTY0ODQ0fSx7IngiOjIyNS45NjkwMjk3NDQ0NjYxMywieSI6NDE0LjM5OTk5Mzg5NjQ4NDR9LHsieCI6Mzk4LjYxMDk5MjQzMTY0MDYsInkiOjQxNC4zOTk5OTM4OTY0ODQ0fSx7IngiOjM5OC42MTA5OTI0MzE2NDA2LCJ5Ijo0NjQuMzk5OTkzODk2NDg0NH0seyJ4IjozOTguNjEwOTkyNDMxNjQwNiwieSI6NTI2LjM5OTk5Mzg5NjQ4NDR9XQ%3D%3D%22%20marker-end%3D%22url\(%23mermaid-_r_bh__flowchart-v2-pointEnd\)%22%3E%3C%2Fpath%3E%3Cpath%20d%3D%22M398.6109924316406%2C594.3999938964844L398.6109924316406%2C669.9999923706055L398.6109924316406%2C775.5999908447266L398.6109924316406%2C818.8170348194319Q398.6109924316406%2C820.5999908447266%20397.52520599401373%2C822.0142044070997L397.52520599401373%2C822.0142044070997Q396.43941955638684%2C823.4284179694728%20395.02520599401373%2C824.5142044070997L395.02520599401373%2C824.5142044070997Q393.6109924316406%2C825.5999908447266%20391.828036406346%2C825.5999908447266L229.29365243642746%2C825.5999908447266Q227.5106964111328%2C825.5999908447266%20226.0964828487597%2C826.6857772823535L226.0964828487597%2C826.6857772823535Q224.68226928638663%2C827.7715637199803%20223.59648284875973%2C829.1857772823535L223.5964828487597%2C829.1857772823535Q222.5106964111328%2C830.5999908447266%20222.5106964111328%2C832.3829468700212L222.5106964111328%2C835.5999908447266%22%20id%3D%22L_J_I_0%22%20class%3D%22edge-thickness-normal%20edge-pattern-solid%20edge-thickness-normal%20edge-pattern-solid%20flowchart-link%22%20style%3D%22%3B%22%20data-edge%3D%22true%22%20data-et%3D%22edge%22%20data-id%3D%22L_J_I_0%22%20data-points%3D%22W3sieCI6Mzk4LjYxMDk5MjQzMTY0MDYsInkiOjU5NC4zOTk5OTM4OTY0ODQ0fSx7IngiOjM5OC42MTA5OTI0MzE2NDA2LCJ5Ijo2NjkuOTk5OTkyMzcwNjA1NX0seyJ4IjozOTguNjEwOTkyNDMxNjQwNiwieSI6Nzc1LjU5OTk5MDg0NDcyNjZ9LHsieCI6Mzk4LjYxMDk5MjQzMTY0MDYsInkiOjgyNS41OTk5OTA4NDQ3MjY2fSx7IngiOjIyMi41MTA2OTY0MTExMzI4LCJ5Ijo4MjUuNTk5OTkwODQ0NzI2Nn0seyJ4IjoyMjIuNTEwNjk2NDExMTMyOCwieSI6ODM5LjU5OTk5MDg0NDcyNjZ9XQ%3D%3D%22%20marker-end%3D%22url\(%23mermaid-_r_bh__flowchart-v2-pointEnd\)%22%3E%3C%2Fpath%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabels%22%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%3E%3Crect%20class%3D%22background%22%20style%3D%22stroke%3A%20none%22%3E%3C%2Frect%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_A_B_0%22%20transform%3D%22translate\(0%2C%200\)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_B_C_0%22%20transform%3D%22translate\(0%2C%200\)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_C_D_0%22%20transform%3D%22translate\(0%2C%200\)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_D_E_0%22%20transform%3D%22translate\(0%2C%200\)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_E_F_0%22%20transform%3D%22translate\(0%2C%200\)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_F_G_0%22%20transform%3D%22translate\(0%2C%200\)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_G_H_0%22%20transform%3D%22translate\(0%2C%200\)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_H_I_0%22%20transform%3D%22translate\(0%2C%200\)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_D_J_0%22%20transform%3D%22translate\(0%2C%200\)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3Cg%20class%3D%22edgeLabel%22%3E%3Cg%20class%3D%22label%22%20data-id%3D%22L_J_I_0%22%20transform%3D%22translate\(0%2C%200\)%22%3E%3Ctext%20y%3D%22-10.1%22%3E%3Ctspan%20class%3D%22text-outer-tspan%22%20x%3D%220%22%20y%3D%22-0.1em%22%20dy%3D%221.1em%22%3E%3C%2Ftspan%3E%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E)

## 5. Definition of done for the whole project

Do not mark the project complete just because it is deployed. It should satisfy all these checks.

## Project completion checklist

### 0/8

Working chat application

Answers questions about synthetic AWS logs through Streamlit and FastAPI.

Grounded AI answers

Provides relevant log citations and acknowledges missing evidence.

Incremental ingestion

Automatically indexes new CloudWatch logs and reloads updated index versions.

Evaluation results

Reports retrieval recall at 8, answer correctness, citation quality and refusal behavior.

Reproducible infrastructure

CDK can create and remove the project's infrastructure.

Secure delivery

Uses least-privilege IAM, OIDC for GitHub Actions and no stored AWS access keys on EC2.

Portfolio materials

Includes a README, architecture diagram, cost breakdown and demonstration.

Verified teardown

No unwanted running resources or continuing project charges remain.

## 6. Scope priorities if you fall behind

Your original plan correctly prioritizes the core application over optional work. Use these tiers:

* Must finish: Phases 0–5 — a tested RAG application deployed to AWS.

* Should finish: Phase 6 — automatic indexing, monitoring and alerts.

* Finish for a strong portfolio: Phase 7 and Phase 8 — CDK, CI/CD, evaluation results and a clean teardown.

* Optional: S3 access-log ingestion and the ECS Fargate/ALB experiment. Do not start the ECS experiment until the core project is finished and your credit balance is healthy.

One final budget note: AWS Free Plan credits are not the same as guaranteed free usage. Check the pricing calculator for your region, configure billing alerts, and monitor actual spend throughout the project.

## 7. How to execute the plan day by day

Start with Phase 0, Task P0-01. Finish one task, run its test, commit the working change to Git, and only then move to the next task.

A useful GitHub issue format for each task is:

* Objective: What needs to be built?

* Prerequisites: Which tasks must be complete first?

* Implementation: Which files or AWS resources will change?

* Acceptance criteria: What must work?

* Test procedure: How will you prove it works?

* Risks: What might fail or cost money?

This turns your project overview into an executable engineering backlog and makes it much easier to debug, track progress, and explain the project during interviews.
