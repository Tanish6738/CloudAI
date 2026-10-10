# Requirements Document

## Introduction

Cloud Ops Copilot is a chat assistant that answers natural language questions about AWS CloudWatch logs using a Retrieval-Augmented Generation (RAG) pipeline. A developer asks a question such as "Why did the checkout Lambda fail at 2 PM?" and the assistant retrieves the most relevant log chunks, passes them to an Amazon Bedrock language model, and returns a grounded answer that cites specific log IDs.

The system is built entirely on AWS free-tier-eligible and credit-covered services. It runs as a containerized application on EC2, uses FAISS for vector search stored on S3, Amazon Bedrock Titan Text Embeddings v2 for embedding, and Amazon Bedrock Nova Lite for answer generation. Infrastructure is managed with AWS CDK (Python) and delivered via GitHub Actions with OIDC federation. The project spans nine phases across fourteen to fifteen days, resulting in a portfolio-grade deliverable with evaluation results, a README, architecture diagram, and a demonstration recording.

---

## Glossary

- **System**: The Cloud Ops Copilot application as a whole.
- **Application**: The containerized process running on EC2 that includes the FastAPI server and the Streamlit UI.
- **LogRecord**: The normalized log object with fields: `id`, `timestamp`, `source`, `service`, `level`, `message`, `attributes`.
- **LogPlugin**: An abstract base class that every log-source adapter must implement; exposes a `fetch(since, until)` method yielding `LogRecord` objects.
- **CloudWatchPlugin**: The concrete `LogPlugin` implementation that reads from Amazon CloudWatch Logs.
- **Chunk**: A group of `LogRecord` objects combined into a single text block of approximately 300–500 tokens, with associated metadata (service, level, time range).
- **Embedder**: The component that calls Bedrock Titan Text Embeddings v2 to produce vectors from chunk text.
- **FAISS_Index**: The FAISS flat inner-product index that stores normalized vectors for similarity search.
- **Vector_Store**: The component that manages the FAISS_Index and the accompanying JSON metadata file.
- **Retriever**: The component that embeds a question and returns the top-8 most relevant chunks, with optional filtering.
- **RAG_Agent**: The component that constructs the prompt, calls the Bedrock Converse API, and returns a cited answer.
- **Memory**: The DynamoDB-backed component that stores and retrieves the last 6 conversation turns per session.
- **Log_Refresher**: The AWS Lambda function that incrementally ingests new CloudWatch logs and updates the FAISS index on S3.
- **Log_Generator**: The AWS Lambda function that writes synthetic sample logs to CloudWatch every 5 minutes.
- **CDK_App**: The Python AWS CDK application in the `infra/` directory that defines all infrastructure resources.
- **CI_CD_Pipeline**: The GitHub Actions workflow that runs tests, builds the Docker image, pushes to ECR, and deploys to EC2 via SSM.
- **Evaluation_Runner**: The script `eval/run_eval.py` that runs 25 questions against the RAG pipeline and records metrics.
- **S3_Index_Bucket**: The S3 bucket that stores the versioned FAISS index and metadata files.
- **Latest_Pointer**: A small file in S3 that records the path to the most recently published index version.
- **Checkpoint**: A timestamp stored in S3 that records the last successfully processed log event time, used by the Log_Refresher for incremental ingestion.

---

## Requirements

### Requirement 1: Development Environment and AWS Safety Setup

**User Story:** As a developer, I want a properly configured local development environment and a guarded AWS account, so that I can build the project safely without unexpected charges.

*Tasks: P0-01 through P0-07*

#### Acceptance Criteria

1. THE System SHALL require the following tools installed and executable before any other phase begins: Python 3.12 or later, Git 2.x or later, Docker 24.x or later, AWS CLI v2, Node.js 18 or later, and CDK CLI 2.x or later.
2. WHEN the AWS CLI is invoked after setup, THE System SHALL report an IAM principal ARN matching the configured administrative identity and the expected deployment region.
3. IF the current AWS account spend has not yet reached $10, $25, or $50 respectively, THEN THE System SHALL have AWS Budgets email alerts configured at those three thresholds before any billable AWS resource is created.
4. WHEN a developer accesses the AWS root account, THE System SHALL require multi-factor authentication before granting console access.
5. THE System SHALL use a dedicated IAM user or IAM Identity Center permission set with AdministratorAccess for day-to-day operations; no workload tasks SHALL be performed while authenticated as the root account.
6. WHEN Bedrock model access is verified on Day 0, THE System SHALL return a non-error response from Amazon Bedrock Nova Lite through the AWS Console playground within 30 seconds of submitting a test prompt.
7. THE System SHALL store all non-secret configuration values such as model IDs, the S3 bucket name, and the AWS region in SSM Parameter Store under the `/cloudops/` path prefix.
8. THE System SHALL tag every AWS resource it creates with the tag `project=cloudops-copilot` to enable resource discovery and cost attribution.

---

### Requirement 2: Repository Structure and Project Foundation

**User Story:** As a developer, I want a well-organized repository with a clear directory structure, so that I can find and modify each component without confusion.

*Tasks: P1-01, P0-02*

#### Acceptance Criteria

1. THE System SHALL organize source code into the following top-level directories: `plugins/`, `core/`, `agent/`, `api/`, `ui/`, `lambdas/`, `infra/`, `eval/`, `tests/`.
2. THE System SHALL include the following root-level files: `Dockerfile`, `docker-compose.yml`, `pyproject.toml`, `.gitignore`, `.env.example`, `README.md`.
3. THE System SHALL exclude all AWS credentials and `.env` files from version control via `.gitignore`.
4. WHEN a developer clones the repository, THE System SHALL provide an `.env.example` file documenting every required environment variable.

---

### Requirement 3: Log Data Model and Plugin Interface

**User Story:** As a developer, I want a consistent log record format and a standard plugin interface, so that log sources can be added or swapped without changing the RAG pipeline.

*Tasks: P1-02, P1-03*

#### Acceptance Criteria

1. THE System SHALL define a `LogRecord` data class in `core/models.py` containing exactly the fields: `id` (str), `timestamp` (datetime), `source` (str), `service` (str), `level` (str), `message` (str), and `attributes` (dict).
2. THE System SHALL define a `LogPlugin` abstract base class in `plugins/base.py` with an abstract method `fetch(since: datetime, until: datetime) -> Iterator[LogRecord]`.
3. WHEN a concrete plugin class is defined, THE System SHALL raise a TypeError at class instantiation time if the `name` attribute is missing or is not a non-empty string.
4. THE System SHALL normalize all log records from any source into the `LogRecord` schema before passing them to the chunking stage.
5. IF a log record is missing a required field, THEN THE System SHALL assign the following sentinel values: `None` for `timestamp`, `""` for all other string fields, and `{}` for `attributes`, and SHALL continue processing rather than raising an unhandled exception.
6. WHEN a plugin's `fetch` method raises an exception, THE System SHALL log the error to CloudWatch Logs, skip that plugin's output for the current run, and continue processing records from other plugins.
7. IF the `attributes` field of a log record is `None`, THEN THE System SHALL normalize it to an empty dict `{}` before passing it downstream.

---

### Requirement 4: CloudWatch Log Ingestion

**User Story:** As a developer, I want a CloudWatch log plugin that reads Lambda logs reliably, so that the RAG pipeline has real log data to work with.

*Tasks: P1-04, P1-05, P1-06, P1-07, P1-08*

#### Acceptance Criteria

1. THE System SHALL provide a `CloudWatchPlugin` in `plugins/cloudwatch_plugin.py` that implements the `LogPlugin` interface and reads from specified CloudWatch log groups.
2. WHEN the `CloudWatchPlugin` fetches logs, THE System SHALL paginate through all available log events within the requested time window (maximum 24 hours per call) by following `nextToken` responses until exhausted, without dropping records.
3. IF no Checkpoint exists for a log group, THEN THE System SHALL fetch all available events in the requested window. WHEN a previous ingestion run has recorded a Checkpoint, THE System SHALL resume from a timestamp strictly greater than the Checkpoint and process only new log events.
4. THE System SHALL provide a `Log_Generator` Lambda in `lambdas/log_generator/` that writes synthetic CloudWatch log events to a named log group every 5 minutes.
5. WHEN the `Log_Generator` Lambda runs, THE System SHALL produce a minimum of 10 log records per invocation, including at least one ERROR-level record and at least one INFO-level record, each containing a timestamp, a log level, and a message text.
6. THE System SHALL include unit tests for the `CloudWatchPlugin` in `tests/` that use `moto` to mock CloudWatch Logs API calls without making real AWS requests.
7. IF the CloudWatch Logs API returns an error during a `fetch` call, THEN THE System SHALL abort the ingestion run for that log group, preserve the existing Checkpoint unchanged, and surface an error message identifying the failed log group and the cause.
8. WHEN zero log events are retrieved for a requested time window, THE System SHALL advance the Checkpoint to the end of that window to prevent reprocessing on the next run.

---

### Requirement 5: Log Chunking and Embedding Pipeline

**User Story:** As a developer, I want logs chunked and embedded into a searchable vector index, so that the retriever can find relevant log content for any natural language question.

*Tasks: P2-01 through P2-10*

#### Acceptance Criteria

1. THE System SHALL implement a `Chunker` in `core/chunker.py` that groups `LogRecord` objects into chunks of 300 to 500 tokens inclusive, splitting at record boundaries (never mid-record).
2. WHEN multiple log records share the same request ID, THE System SHALL group them into the same chunk before applying the token-size limit; IF a request-ID group exceeds 500 tokens, THE System SHALL split it into sequential sub-chunks each within the 300–500 token bound.
3. WHEN log records do not share a request ID, THE System SHALL group them by service name and 60-second time windows.
4. THE System SHALL attach the following metadata to every chunk: service name, severity level, and the time range covered by the records in the chunk.
5. THE System SHALL deduplicate log records before chunking, keeping the first occurrence in ingestion order and discarding any subsequent record with a duplicate `id` field.
6. THE System SHALL implement an `Embedder` in `core/embedder.py` that calls Bedrock Titan Text Embeddings v2 and returns a normalized float vector for each chunk.
7. WHEN the Bedrock embedding API returns a throttling error, THE System SHALL retry the request up to 3 times with delays of 1, 2, and 4 seconds respectively; IF all retries are exhausted, THE System SHALL propagate the failure to the caller.
8. WHEN embedding a batch of chunks, THE System SHALL submit sub-batches of at most 25 chunks per API call.
9. THE System SHALL implement a `Vector_Store` in `core/vector_store.py` that maintains a FAISS flat inner-product index over normalized embedding vectors.
10. THE System SHALL align vector IDs in the FAISS_Index with record IDs in the JSON metadata file so that a vector ID always maps to exactly one metadata entry.
11. WHEN the FAISS_Index and metadata file are saved to S3, THE System SHALL write them to a versioned path prefix (e.g., `index/v{timestamp}/`) and update the Latest_Pointer file.
12. WHEN the Vector_Store is loaded from S3, THE System SHALL read the Latest_Pointer file to determine which version to load.
13. WHEN a saved index is reloaded from S3 and queried with a fixed vector, THE System SHALL return the same top-5 document IDs in the same rank order as the pre-save query, confirming a successful round-trip.

---

### Requirement 6: Retrieval and RAG Answer Generation

**User Story:** As a developer, I want the RAG pipeline to retrieve relevant log chunks and generate grounded, cited answers, so that users receive accurate responses backed by real log evidence.

*Tasks: P3-01 through P3-06*

#### Acceptance Criteria

1. WHEN the FAISS_Index contains at least 1 chunk, THE System SHALL implement a `Retriever` in `agent/retriever.py` that embeds an input question and returns the top-8 most similar chunks; IF the index contains fewer than 8 chunks, THE System SHALL return all available chunks.
2. WHEN a user query includes a service name filter, THE System SHALL restrict retrieval results to chunks whose metadata service field matches the filter using case-insensitive exact string comparison.
3. WHEN a user query includes a severity level filter, THE System SHALL restrict retrieval results to chunks whose metadata level field matches the filter using case-insensitive exact string comparison.
4. WHEN a user query includes a time range filter, THE System SHALL restrict retrieval results to chunks whose time range has any overlap with the specified interval (partial or full intersection; a single-timestamp chunk is included if its timestamp falls within the interval).
5. THE System SHALL implement a `RAG_Agent` in `agent/rag_agent.py` that constructs a prompt containing the retrieved chunks and calls the Bedrock Converse API to generate an answer.
6. WHEN constructing the prompt, THE System SHALL instruct the Bedrock model to answer only from the provided log evidence and to cite the chunk identifier of each supporting record in the answer text.
7. WHEN the retrieved chunks do not contain evidence to answer the question, THE System SHALL return a response whose text states that no supporting evidence was found in the available logs, and SHALL NOT include any fabricated log data or log IDs.
8. IF the Bedrock Converse API returns an error, THEN THE System SHALL return a response that indicates the request failed and SHALL NOT include internal error details such as stack traces or AWS error codes in the API response body.
9. THE System SHALL read the model ID from SSM Parameter Store at runtime on each invocation, so that changing the SSM parameter value takes effect on the next request without modifying any source files.

---

### Requirement 7: Evaluation Suite

**User Story:** As a developer, I want a structured evaluation dataset and runner, so that I can measure retrieval quality and answer accuracy across Bedrock models.

*Tasks: P3-07, P3-08, P3-09*

#### Acceptance Criteria

1. THE System SHALL provide an evaluation dataset of exactly 25 questions, each entry containing: a natural-language question, a single correct reference answer, and one or more expected supporting log IDs.
2. THE System SHALL include at least 3 questions covering each of the following failure scenarios in the synthetic logs: database connection timeout, permission error, and cold-start latency spike (minimum 9 questions total across these three scenarios).
3. THE System SHALL implement an `Evaluation_Runner` that runs all 25 questions against the RAG pipeline and records, for each question: the retrieved log IDs, the generated answer text, and a pass/fail verdict for both citation and refusal checks.
4. WHEN the `Evaluation_Runner` executes, THE System SHALL compute recall at k=8 as the proportion of questions for which at least one expected log ID appears in the top 8 retrieved documents, and include this value in the run summary output.
5. WHEN the `Evaluation_Runner` executes, THE System SHALL mark a question as citation-pass if the generated answer contains at least one expected log ID verbatim, and mark it citation-fail otherwise.
6. WHEN the `Evaluation_Runner` executes, THE System SHALL mark a question as refusal-pass if the RAG_Agent returns a response indicating no answer can be provided when zero retrieved documents have a relevance score above 0.5, and mark it refusal-fail if a substantive answer is generated under that condition.
7. THE System SHALL store one JSON result file per run containing: the UTC timestamp in ISO 8601 format, the model ID used, the per-question verdicts, and the recall@8 score.
8. THE System SHALL support running the `Evaluation_Runner` against Nova Micro, Nova Lite, and Nova 2 Lite by accepting the model ID via a `--model-id` CLI argument, and SHALL exit with a non-zero status code and an error message if an unrecognized model ID is provided.

---

### Requirement 8: API Server and Session Memory

**User Story:** As a developer, I want a FastAPI server with persistent session memory, so that users can have multi-turn conversations about their logs.

*Tasks: P4-01 through P4-06*

#### Acceptance Criteria

1. THE System SHALL implement the API server using FastAPI.
2. THE System SHALL expose a `GET /health` endpoint that returns HTTP 200 and a JSON response body containing a `status` field with the value `"ok"`.
3. THE System SHALL expose a `POST /chat` endpoint that accepts a JSON body containing a `session_id` string of 1–128 characters and a `question` string of 1–1000 characters, and returns a JSON body containing an `answer` string and a `cited_log_ids` list of up to 20 log ID strings.
4. IF the `POST /chat` endpoint receives a request with an empty, missing, or out-of-bounds `session_id` or `question` field, THEN THE System SHALL return HTTP 422 with a validation error message identifying which field failed and the reason.
5. THE System SHALL implement a `Memory` component that reads and writes conversation history to a DynamoDB table keyed by `session_id`.
6. WHEN a session has more than 6 prior turns, THE System SHALL retain only the most recent 6 turns in DynamoDB by deleting the oldest turn record, and SHALL pass only those 6 retained turns as context to the RAG_Agent.
7. WHEN the `POST /chat` endpoint processes a request, THE System SHALL append the question and answer as a new turn to the session history in DynamoDB after generating the response.
8. THE System SHALL validate the structure of all request and response bodies using Pydantic models.
9. IF the DynamoDB table is unavailable when the `POST /chat` endpoint attempts to read session history, THEN THE System SHALL return HTTP 503 with an error message indicating that the service is temporarily unavailable.
10. IF the DynamoDB table is unavailable when the `POST /chat` endpoint attempts to write session history after generating a response, THEN THE System SHALL return the generated answer to the caller and include a `warning` field in the response body indicating that session history could not be saved.

---

### Requirement 9: Streamlit User Interface and Local Development

**User Story:** As a developer, I want a Streamlit chat interface that connects to the FastAPI server, so that I can interact with the assistant through a browser during local development.

*Tasks: P4-07, P4-08, P4-09, P4-10*

#### Acceptance Criteria

1. THE System SHALL implement the Streamlit application in `ui/app.py` that renders a chat interface with a text input and a message history display.
2. WHEN a user submits a question in the Streamlit interface, THE System SHALL send the question to the FastAPI `POST /chat` endpoint and display the returned answer.
3. WHEN the FastAPI server returns cited log IDs, THE System SHALL display those citations alongside the answer text in the Streamlit interface.
4. THE System SHALL provide a `docker-compose.yml` file that starts the FastAPI server and the Streamlit application as separate services with correct port bindings.
5. WHEN `docker-compose up` is run on a developer laptop, THE System SHALL make the Streamlit UI accessible at port 8501 and the FastAPI server accessible at port 8000.
6. THE System SHALL include integration tests in `tests/` that verify the `/health` endpoint returns 200, the `/chat` endpoint returns a valid response schema, and the `/chat` endpoint handles error conditions gracefully.

---

### Requirement 10: Container Image and AWS Deployment

**User Story:** As a developer, I want a production-ready container image deployed on EC2 with locked-down access, so that I can run the application in AWS securely.

*Tasks: P5-01 through P5-10*

#### Acceptance Criteria

1. THE System SHALL provide a production `Dockerfile` that builds a runnable image of the FastAPI and Streamlit application without including AWS credentials or `.env` files.
2. WHEN the container image is built and run locally, THE System SHALL start both the FastAPI service on port 8000 and the Streamlit service on port 8501 within 60 seconds, with no process exit errors, and both services shall respond to a health probe before the image is pushed to ECR.
3. THE System SHALL create a private ECR repository to host the application image, and tag the pushed image with a version identifier.
4. THE System SHALL attach a least-privilege IAM instance role to the EC2 instance that grants only: read access to the index prefix in S3, invocation of the Bedrock models listed in the project configuration, read/write access to the DynamoDB session table, and read access to SSM parameters under `/cloudops/`.
5. THE System SHALL deploy the application on a single EC2 t3.micro instance in the default VPC on a public subnet.
6. THE System SHALL configure the EC2 security group to allow inbound TCP traffic on ports 8000 and 8501 only from a single IPv4 CIDR derived from the developer's current public IP address (formatted as `<IP>/32`), and deny all other inbound traffic on those ports.
7. THE System SHALL configure SSM Session Manager on the EC2 instance to provide shell access without opening port 22.
8. WHEN the container is running on EC2 and the request source IP matches the permitted `/32` CIDR, THE System SHALL respond with a non-error HTTP status to `GET /health` within 5 seconds and accept `POST /chat` requests on port 8000.
9. THE System SHALL require IMDSv2 on the EC2 instance by setting the HTTP token requirement to `required` with a hop limit of 1.
10. THE System SHALL encrypt the EBS root volume of the EC2 instance using the default AWS-managed key for EBS.
11. THE System SHALL block all public access settings on every S3 bucket used by the application.
12. THE System SHALL enable versioning on the S3_Index_Bucket.

---

### Requirement 11: Automated Log Refresh and Index Hot-Reload

**User Story:** As a developer, I want new CloudWatch logs to become searchable automatically without restarting the application, so that the index stays current.

*Tasks: P6-01 through P6-07*

#### Acceptance Criteria

1. THE System SHALL implement a `Log_Refresher` Lambda function in `lambdas/log_refresher/` that reads new CloudWatch log events since the last Checkpoint, embeds them, appends them to the current FAISS index, and writes a new versioned index to S3.
2. WHEN the `Log_Refresher` runs and at least one new log event exists since the Checkpoint, THE System SHALL read the Checkpoint from S3, process only those new events, write the updated index, update the Latest_Pointer, and only then write the updated Checkpoint.
3. THE System SHALL package the `Log_Refresher` Lambda with a FAISS binary compiled for the Lambda execution environment's CPU architecture (x86_64 or arm64) either through a Lambda layer or an included package.
4. WHEN the `Log_Refresher` publishes a new index version, THE System SHALL update the Latest_Pointer file in S3 to reference the new version path.
5. WHEN the `Log_Refresher` runs and zero new log events exist since the Checkpoint, THE System SHALL leave the index, Latest_Pointer, and Checkpoint unchanged.
6. WHEN the Application polls S3 for the Latest_Pointer and detects a change, THE System SHALL reload the FAISS_Index from S3 within 30 seconds of detecting the change, without restarting the container process.
7. THE System SHALL schedule the `Log_Refresher` Lambda to run every 30 minutes using an Amazon EventBridge rule.
8. WHEN a manual invocation of the `Log_Refresher` is triggered and new logs exist, THE System SHALL make those logs searchable through the API within 60 seconds of the index reload completing.
9. IF an S3 write operation fails during the refresh, THE System SHALL abort the refresh, preserve the existing index, Latest_Pointer, and Checkpoint unchanged, and return an error to the Lambda runtime indicating which S3 operation failed.

---

### Requirement 12: Monitoring, Alerting, and Observability

**User Story:** As a developer, I want CloudWatch alarms and SNS email notifications, so that I am alerted when the log refresher fails or other operational issues occur.

*Tasks: P6-08, P6-09, P6-10*

#### Acceptance Criteria

1. THE System SHALL configure CloudWatch alarms that trigger on `Log_Refresher` Lambda invocation errors.
2. WHEN a CloudWatch alarm transitions to the ALARM state, THE System SHALL publish a notification to an SNS topic that delivers an email to the configured developer address.
3. THE System SHALL create a CloudWatch dashboard that displays at minimum: `Log_Refresher` Lambda invocation count, error count, and duration; EC2 CPU utilization; and DynamoDB read/write capacity consumption.
4. WHEN the `Log_Refresher` is intentionally forced to fail in a test, THE System SHALL send an email notification via SNS within the CloudWatch alarm evaluation period.
5. THE System SHALL configure the SNS topic to deliver to a verified email address before any alarm is activated.

---

### Requirement 13: Infrastructure as Code with AWS CDK

**User Story:** As a developer, I want all AWS resources defined in a CDK Python application, so that the entire environment can be created and destroyed reproducibly with a single command.

*Tasks: P7-01 through P7-09*

#### Acceptance Criteria

1. THE System SHALL define a Python CDK application in the `infra/` directory that provisions all project resources defined in criterion 2.
2. THE CDK_App SHALL define the following resource groups: S3 bucket with versioning and blocked public access; ECR repository; DynamoDB table; SSM parameters; Lambda functions with EventBridge schedules and IAM roles; CloudWatch alarms and SNS topic; EC2 instance with instance profile, security group, and EBS volume.
3. WHEN `cdk synth` is run, THE CDK_App SHALL produce a valid CloudFormation template and exit with a zero return code.
4. WHEN `cdk deploy` is run on an AWS account that contains none of the stack's resources, THE CDK_App SHALL create all resource groups listed in criterion 2, with each resource reachable and operational within 30 minutes of the command completing.
5. WHEN `cdk destroy` is run, THE CDK_App SHALL delete all provisioned resources except S3 bucket contents and DynamoDB table data, which SHALL be retained via a RemovalPolicy of RETAIN, and SHALL leave no stack resources in a billable active state.
6. THE CDK_App SHALL apply the `project=cloudops-copilot` tag to every resource it creates.
7. THE CDK_App SHALL configure encryption at rest on the EBS volume and the DynamoDB table.
8. WHEN hand-built resources are replaced by CDK-managed resources, THE System SHALL complete the migration with zero data loss, verified by record count equality before and after migration, and with no more than 10 minutes of service unavailability per resource group.

---

### Requirement 14: CI/CD Pipeline with GitHub Actions and OIDC

**User Story:** As a developer, I want a GitHub Actions pipeline that builds, tests, and deploys the application automatically on every push to main, so that the running environment always reflects the latest code.

*Tasks: P7-10, P7-11, P7-12*

#### Acceptance Criteria

1. WHEN a push or pull request event is received by GitHub Actions, THE CI_CD_Pipeline SHALL trigger a workflow job that executes the full `pytest` test suite and reports the result as a GitHub commit status check on the triggering commit.
2. THE System SHALL configure GitHub OIDC federation with AWS so that the GitHub Actions workflow obtains AWS credentials scoped to the duration of the workflow job only, with no long-lived access keys stored anywhere in the repository or GitHub Actions secrets.
3. WHEN the `pytest` test suite passes on a push to the `main` branch, THE CI_CD_Pipeline SHALL build the production Docker image and push it to ECR, tagging the image with the full Git commit SHA.
4. WHEN the image is successfully pushed to ECR, THE CI_CD_Pipeline SHALL issue an SSM Run Command to the target EC2 instance that pulls the new image from ECR and restarts the running container, and SHALL fail the workflow step if the SSM command does not complete within 300 seconds.
5. THE System SHALL store no AWS access keys or secrets in GitHub Actions secrets; all AWS access SHALL be obtained exclusively through the OIDC role configured in criterion 2.
6. WHEN a pull request is opened or updated, THE CI_CD_Pipeline SHALL run the `pytest` test suite and publish the pass/fail result as a GitHub pull request status check without executing any deployment steps against EC2.

---

### Requirement 15: End-to-End Validation and Portfolio Delivery

**User Story:** As a developer, I want a complete end-to-end validation, finished portfolio materials, and a clean teardown, so that the project is ready to present and leaves no ongoing AWS charges.

*Tasks: P8-01 through P8-10*

#### Acceptance Criteria

1. THE System SHALL pass a complete end-to-end test that covers log generation, ingestion, embedding, indexing, retrieval, and answer generation in sequence.
2. THE System SHALL produce a final evaluation results table in `eval/results/` comparing Nova Micro, Nova Lite, and Nova 2 Lite across recall@8, citation accuracy, and refusal rate.
3. THE System SHALL include a `README.md` at the repository root containing: project description, architecture diagram, cost breakdown for the 14-day run, setup instructions, teardown instructions, and a summary of evaluation results.
4. THE System SHALL include an architecture diagram (image file or embedded Mermaid diagram) that accurately represents all AWS services and the data flow between them.
5. WHEN the project is complete, THE System SHALL have a demonstration recording of approximately 3 minutes showing a live question-and-answer session through the Streamlit UI.
6. WHEN `cdk destroy` is run at project end, THE System SHALL remove all billable resources including the EC2 instance, EBS volume, Elastic IP, S3 objects, ECR images, and Lambda functions.
7. WHEN teardown is complete, THE System SHALL confirm through a Tag Editor search that no resources tagged `project=cloudops-copilot` remain in the account.
8. WHEN teardown is complete, THE System SHALL confirm on the AWS Billing console the following day that no new charges are accruing.
9. WHERE the developer has sufficient time and credits, THE System SHALL optionally provide an `S3AccessLogPlugin` in `plugins/s3_access_plugin.py` that implements the `LogPlugin` interface for S3 server access logs.
10. WHERE the S3AccessLogPlugin is implemented, THE System SHALL parse S3 access log lines into `LogRecord` objects using the documented S3 server access log format.

---

### Requirement 16: Security Baseline

**User Story:** As a developer, I want the application to follow AWS security best practices throughout, so that the project is safe to run and appropriate to include in a portfolio.

*Tasks: P5-05, P5-09, P0-03, P0-04 (security aspects)*

#### Acceptance Criteria

1. THE System SHALL use IAM roles for all AWS service access from EC2 and Lambda; no long-lived access keys SHALL be stored on any compute resource.
2. THE System SHALL require IMDSv2 on the EC2 instance, preventing unauthenticated access to instance metadata.
3. THE System SHALL keep port 22 closed on the EC2 security group and provide shell access exclusively through SSM Session Manager.
4. THE System SHALL block all S3 bucket public access at the bucket policy level.
5. THE System SHALL encrypt all EBS volumes and the DynamoDB table at rest using AWS-managed keys.
6. THE System SHALL scope the EC2 instance role to read only the specific S3 prefix used for the FAISS index, not the entire bucket.
7. THE System SHALL scope each Lambda execution role to the minimum set of CloudWatch log groups, S3 prefixes, and Bedrock model ARNs required for that function's operation.
8. THE System SHALL store only sample or synthetic log data; no real customer or personal data SHALL be ingested or indexed.
9. IF a request to the Bedrock API fails due to an authorization or quota error, THEN THE System SHALL log the error details to CloudWatch Logs without exposing them in the API response body.
