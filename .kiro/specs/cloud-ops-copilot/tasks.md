# Implementation Plan: Cloud Ops Copilot

## Overview

This plan converts the Cloud Ops Copilot design into incremental coding tasks across nine phases. Each task builds on the previous ones and ends with wired, tested components. The implementation language is **Python 3.12** throughout, using pytest + Hypothesis for testing, FastAPI + Streamlit for the application layer, FAISS + Amazon Bedrock for the RAG pipeline, and AWS CDK (Python) for infrastructure.

**Priority tiers:**
- **Required (Phases 0–5, 8):** Core application — must be completed.
- **Recommended (Phases 6–7):** Automated refresh, monitoring, CDK, CI/CD — strong portfolio.
- **Optional:** S3AccessLogPlugin (Task 8.2).

---

## Tasks

### Phase 0 — Environment Setup and AWS Guardrails

- [~] 1. Set up local development tools and verify installations
  - Install Python 3.12+, Git 2.x+, Docker 24.x+, AWS CLI v2, Node.js 18+, CDK CLI 2.x
  - Run `python --version`, `git --version`, `docker --version`, `aws --version`, `node --version`, `cdk --version` and confirm each exits with a zero return code
  - _Requirements: 1.1_

- [ ] 2. Create GitHub repository and initialize project skeleton
  - [~] 2.1 Create GitHub repository `cloudops-copilot` with a default branch named `main`
    - Add a `.gitignore` that excludes `.env`, `*.pem`, `**/__pycache__`, `.venv`, `*.egg-info`, `.pytest_cache`, and `cdk.out`
    - Add a root `README.md` with a project title placeholder
    - _Requirements: 2.1, 2.2, 2.3_
  - [ ]* 2.2 Verify `.gitignore` excludes credential files
    - Create a dummy `.env` file, run `git status`, confirm it is untracked
    - Delete the dummy file
    - _Requirements: 2.3_

- [ ] 3. Secure AWS account and configure IAM identity
  - [~] 3.1 Enable MFA on the AWS root account
    - Document the MFA ARN (do not commit to Git)
    - _Requirements: 1.4_
  - [~] 3.2 Create an administrative IAM identity (IAM user or IAM Identity Center permission set) with `AdministratorAccess`
    - Configure AWS CLI profile and run `aws sts get-caller-identity`; confirm the returned ARN matches the admin identity and the expected region
    - _Requirements: 1.2, 1.5_

- [ ] 4. Configure AWS Budgets and verify Bedrock access
  - [~] 4.1 Create three AWS Budgets email alerts at $10, $25, and $50 thresholds
    - Use `aws budgets create-budget` or the console; confirm all three alerts appear under AWS Budgets
    - _Requirements: 1.3_
  - [~] 4.2 Verify Bedrock Nova Lite model access in the AWS Console playground
    - Submit a test prompt and confirm a non-error response is returned
    - _Requirements: 1.6_

- [ ] 5. Set up SSM Parameter Store and resource tagging convention
  - [~] 5.1 Create SSM String parameters under the `/cloudops/` path prefix
    - Create: `/cloudops/bedrock/model-id`, `/cloudops/bedrock/embedding-model-id`, `/cloudops/bedrock/region`, `/cloudops/s3/bucket-name`, `/cloudops/s3/index-prefix`, `/cloudops/dynamodb/table-name`, `/cloudops/log-groups`
    - Use placeholder values for bucket-name until S3 is provisioned
    - _Requirements: 1.7_
  - [~] 5.2 Tag every manually created AWS resource with `project=cloudops-copilot`
    - Apply the tag to the IAM user/role, Budget, and SSM parameters where supported
    - _Requirements: 1.8_

- [~] 6. Phase 0 checkpoint
  - Ensure all tools are installed and verified, IAM identity is active, budget alerts exist, Bedrock responds, and SSM parameters are populated. Ask the user if questions arise.

---

### Phase 1 — Repository Foundation and Log Ingestion

- [ ] 7. Create the full project directory structure
  - [~] 7.1 Create the top-level directory skeleton
    - Create directories: `plugins/`, `core/`, `agent/`, `api/`, `ui/`, `lambdas/log_generator/`, `lambdas/log_refresher/`, `infra/`, `eval/`, `tests/`
    - Add `__init__.py` files to all Python package directories
    - Create root files: `Dockerfile` (placeholder), `docker-compose.yml` (placeholder), `pyproject.toml`, `.env.example`
    - _Requirements: 2.1, 2.2, 2.4_
  - [~] 7.2 Set up `pyproject.toml` with project metadata and dependencies
    - Add dependencies: `boto3`, `faiss-cpu`, `hypothesis`, `pytest`, `moto[s3,cloudwatch,dynamodb,ssm]`, `fastapi`, `uvicorn`, `streamlit`, `httpx`, `pydantic>=2`, `aws-cdk-lib`, `constructs`
    - Configure `[tool.pytest.ini_options]` with `addopts = "--tb=short"`
    - _Requirements: 2.1_

- [ ] 8. Implement the `LogRecord` data model and sentinel normalization
  - [~] 8.1 Implement `LogRecord` dataclass in `core/models.py`
    - Define fields: `id` (str), `timestamp` (Optional[datetime]), `source` (str), `service` (str), `level` (str), `message` (str), `attributes` (dict)
    - Implement `__post_init__` that normalizes `None` attributes to `{}`, `None` string fields to `""`, and leaves `timestamp` as `None` when absent
    - _Requirements: 3.1, 3.4, 3.5, 3.7_
  - [ ]* 8.2 Write property test for `LogRecord` normalization
    - **Property 1: LogRecord Normalization Produces Valid Sentinels**
    - **Validates: Requirements 3.4, 3.5, 3.7**
    - Use Hypothesis `@given` with `st.fixed_dictionaries` including optional missing/`None` fields
    - Assert `attributes` is always a `dict`, `timestamp` is `datetime | None`, all string fields are non-`None` `str`
    - `@settings(max_examples=100)`
    - _Requirements: 3.4, 3.5, 3.7_

- [ ] 9. Implement the `LogPlugin` abstract base class
  - [~] 9.1 Implement `LogPlugin` ABC in `plugins/base.py`
    - Define `name: str` class attribute requirement enforced via `__init_subclass__`
    - Raise `TypeError` at class definition time when `name` is missing, `None`, or an empty/whitespace string
    - Define abstract method `fetch(since: datetime, until: datetime) -> Iterator[LogRecord]`
    - _Requirements: 3.2, 3.3_
  - [ ]* 9.2 Write unit tests for plugin name enforcement
    - Test three cases: missing `name`, empty string `name`, `None` `name` — all should raise `TypeError` at class definition time
    - Test one passing case: non-empty `name` string
    - _Requirements: 3.3_

- [ ] 10. Implement the `CloudWatchPlugin`
  - [~] 10.1 Implement `CloudWatchPlugin` in `plugins/cloudwatch_plugin.py`
    - Accept a list of log group names at construction
    - Implement `fetch()` using `boto3` `filter_log_events` with `nextToken` pagination until exhausted
    - Normalize each CloudWatch event into a `LogRecord` using the sentinel rules from `core/models.py`
    - Apply exponential-backoff retry (`ThrottlingException`, `ServiceUnavailableException`) with delays of 1 s, 2 s, 4 s before raising
    - On API error: log the error with group name and error code, leave checkpoint unchanged, return zero records for that group
    - _Requirements: 4.1, 4.2, 4.7_
  - [~] 10.2 Implement checkpoint load and save logic in `CloudWatchPlugin`
    - Load checkpoint from `s3://bucket/checkpoints/{log-group-name}.json`; if absent, use `since` from `fetch()` arguments
    - Resume from timestamp strictly greater than the checkpoint
    - When zero events are retrieved, advance the checkpoint to `until`
    - Save the checkpoint only after successfully yielding all records
    - _Requirements: 4.3, 4.8_
  - [ ]* 10.3 Write property test for CloudWatch pagination completeness
    - **Property 9: CloudWatch Pagination Drops No Records**
    - **Validates: Requirement 4.2**
    - Use `moto` to create a CloudWatch log group with N pages of M events each
    - Use Hypothesis to vary N (1–5) and M (1–20)
    - Assert `len(list(plugin.fetch(...)))` equals N × M
    - `@settings(max_examples=100)`
    - _Requirements: 4.2_
  - [ ]* 10.4 Write property test for checkpoint resume exclusion
    - **Property 10: Checkpoint Resume Excludes Already-Processed Events**
    - **Validates: Requirement 4.3**
    - Use Hypothesis to generate a list of events with arbitrary timestamps and a checkpoint timestamp T
    - Assert that `fetch()` with checkpoint T yields only events with timestamp strictly greater than T
    - Use `moto` for CloudWatch Logs mocking
    - `@settings(max_examples=100)`
    - _Requirements: 4.3_

- [ ] 11. Implement the `Log Generator` Lambda
  - [~] 11.1 Implement `lambdas/log_generator/handler.py`
    - Write a Lambda handler that publishes at least 10 synthetic CloudWatch log events per invocation to a named log group
    - Include at least one ERROR-level event and at least one INFO-level event per invocation
    - Each event must contain a timestamp (ISO 8601), a log level, a service name, a message, and a `request_id` attribute
    - Read the target log group name from the `LOG_GROUP_NAME` environment variable
    - _Requirements: 4.4, 4.5_
  - [ ]* 11.2 Write unit tests for the Log Generator Lambda
    - Invoke the handler in-process using `moto` mock CloudWatch Logs
    - Assert at least 10 records were written, at least one is ERROR level, at least one is INFO level
    - _Requirements: 4.5_

- [~] 12. Phase 1 checkpoint
  - Ensure `LogRecord` normalization passes property tests, `CloudWatchPlugin` passes pagination and checkpoint tests, `LogPlugin` name enforcement is verified. Run `pytest tests/` and confirm all tests pass. Ask the user if questions arise.

---

### Phase 2 — Chunking, Embeddings, and Vector Storage

- [ ] 13. Implement log normalization and deduplication
  - [~] 13.1 Implement `deduplicate()` in `core/chunker.py`
    - Accept a list of `LogRecord` objects; return a list with the first occurrence of each `id` kept, all subsequent duplicates discarded, in original ingestion order
    - _Requirements: 5.5_
  - [ ]* 13.2 Write property test for deduplication idempotence
    - **Property 3: Deduplication Is Idempotent and Produces Unique IDs**
    - **Validates: Requirement 5.5**
    - Use Hypothesis to generate lists of `LogRecord` objects with arbitrary duplicate IDs
    - Assert `deduplicate(records) == deduplicate(deduplicate(records))`
    - Assert the output contains no two records with the same `id`
    - `@settings(max_examples=100)`
    - _Requirements: 5.5_

- [ ] 14. Implement the `Chunker`
  - [~] 14.1 Implement `Chunker.chunk()` in `core/chunker.py`
    - Group records with the same `request_id` attribute together first; split request-ID groups that exceed 500 tokens into sequential sub-chunks
    - For records without a shared `request_id`, group by service name and 60-second time windows
    - Each `Chunk` must contain 300–500 tokens (using 4 chars = 1 token approximation); the 300-token lower bound is waived only when a single record alone exceeds 500 tokens
    - Attach metadata: `service`, dominant `level` (ERROR > WARN > INFO > DEBUG), `time_start`, `time_end`, `record_ids`
    - Generate a UUID4 `chunk_id` per chunk
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  - [ ]* 14.2 Write property test for chunker token bounds
    - **Property 2: Chunker Produces Chunks Within Token Bounds**
    - **Validates: Requirements 5.1, 5.2, 5.3**
    - Use Hypothesis to generate non-empty lists of `LogRecord` objects
    - Assert every produced chunk contains 300–500 tokens, except single-record oversized chunks
    - `@settings(max_examples=100)`
    - _Requirements: 5.1, 5.2, 5.3_

- [ ] 15. Implement the `Embedder`
  - [~] 15.1 Implement `Embedder` in `core/embedder.py`
    - Call Bedrock Titan Text Embeddings v2 (`amazon.titan-embed-text-v2:0`) with L2 normalization enabled
    - Submit sub-batches of at most 25 chunks per Bedrock API call
    - Return a list of normalized float vectors of dimension 1024, one per input chunk
    - On `ThrottlingException`: retry up to 3 times with delays of 1 s, 2 s, 4 s; re-raise after the third failure
    - Read the embedding model ID from SSM Parameter Store at `/cloudops/bedrock/embedding-model-id`
    - _Requirements: 5.6, 5.7, 5.8_
  - [ ]* 15.2 Write property test for embedder batch completeness
    - **Property 6: Embedding Batching Preserves Completeness**
    - **Validates: Requirement 5.8**
    - Use Hypothesis to generate chunk lists of arbitrary length (0–100)
    - Mock the Bedrock client to return a fixed-dimension vector per call
    - Assert no single Bedrock call receives more than 25 chunks
    - Assert total vectors returned equals total input chunks
    - `@settings(max_examples=100)`
    - _Requirements: 5.8_
  - [ ]* 15.3 Write unit tests for embedder retry logic
    - Mock Bedrock to raise `ThrottlingException` N times then succeed; test N = 1, 2, 3
    - Assert that after 3 failures the exception propagates
    - Assert retry delays are approximately 1 s, 2 s, 4 s
    - _Requirements: 5.7_

- [ ] 16. Implement the `VectorStore`
  - [~] 16.1 Implement `VectorStore` in `core/vector_store.py`
    - Use `faiss.IndexFlatIP` over normalized 1024-dim vectors
    - Maintain a parallel list of chunk metadata dicts keyed by FAISS integer ID
    - Implement `add(vectors, chunks)` that appends vectors and metadata, keeping `faiss_id` values aligned with metadata list indices
    - Implement `search(query_vector, k=8)` that returns the top-k `(faiss_id, score)` pairs
    - _Requirements: 5.9, 5.10_
  - [~] 16.2 Implement S3 persistence for the `VectorStore`
    - Implement `save_to_s3(bucket, prefix)` that writes `faiss.index` and `metadata.json` (matching `VectorMetadata` schema from the design) to `s3://{bucket}/{prefix}index/v{timestamp}/`
    - After writing both files, overwrite `s3://{bucket}/{prefix}index/latest` with the new version path
    - Implement `load_from_s3(bucket, prefix)` that reads the latest-pointer file and downloads the corresponding index and metadata
    - _Requirements: 5.11, 5.12_
  - [~] 16.3 Enable S3 bucket versioning and public-access blocking
    - In the VectorStore setup/integration code, assert the target S3 bucket has versioning enabled and all public access blocked
    - _Requirements: 10.11, 10.12_
  - [ ]* 16.4 Write property test for vector store round-trip
    - **Property 4: Vector Store Round-Trip Preserves Query Results**
    - **Validates: Requirement 5.13**
    - Use Hypothesis to generate collections of chunks with pre-computed normalized vectors
    - Save to a mocked S3 bucket (moto), reload, query with a fixed unit-norm vector
    - Assert the top-5 `chunk_id` values and rank order are identical before and after the round-trip
    - `@settings(max_examples=100)`
    - _Requirements: 5.13_

- [~] 17. Phase 2 checkpoint
  - Run `pytest tests/` and confirm deduplication, chunker, embedder, and vector store property tests all pass. Manually verify the FAISS round-trip with a small synthetic dataset. Ask the user if questions arise.

---

### Phase 3 — Retrieval, RAG Agent, and Evaluation

- [ ] 18. Implement the `Retriever`
  - [~] 18.1 Implement `Retriever` in `agent/retriever.py`
    - Embed an input question using `Embedder`, query the in-memory `VectorStore` for the top-8 chunks
    - If the index contains fewer than 8 chunks, return all available chunks
    - Apply post-search filters: service name (case-insensitive exact match), severity level (case-insensitive exact match), time range (any overlap with `[time_start, time_end]` inclusive; single-timestamp chunks included if timestamp falls within the interval)
    - Return a list of `Chunk` objects satisfying all active filters
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  - [ ]* 18.2 Write property test for retrieval filter soundness
    - **Property 5: Retrieval Filters Are Sound**
    - **Validates: Requirements 6.2, 6.3, 6.4**
    - Use Hypothesis to generate a vector store with arbitrary chunks and arbitrary non-None filter combinations
    - Assert every returned chunk satisfies all active filter predicates
    - Use an in-memory FAISS index (no S3 mocking needed)
    - `@settings(max_examples=100)`
    - _Requirements: 6.2, 6.3, 6.4_

- [ ] 19. Implement the `RAG Agent`
  - [~] 19.1 Implement `RAG_Agent` in `agent/rag_agent.py`
    - Accept retrieved chunks and conversation history; construct a prompt that instructs the model to answer only from the provided log evidence and to cite the `chunk_id` of each supporting record
    - Call the Bedrock Converse API using the model ID read from SSM at `/cloudops/bedrock/model-id` on every invocation
    - Parse the response to extract `cited_log_ids` (up to 20 IDs)
    - _Requirements: 6.5, 6.6, 6.9_
  - [~] 19.2 Implement refusal and error handling in `RAG_Agent`
    - When no retrieved chunk has a relevance score above 0.5, return a fixed refusal message stating no supporting evidence was found; set `cited_log_ids = []`
    - On `ClientError` from Bedrock: log full error to CloudWatch Logs; return `{"detail": "Answer generation failed. Please try again."}` without stack traces or AWS error codes
    - _Requirements: 6.7, 6.8_
  - [ ]* 19.3 Write property test for no fabricated citations
    - **Property 8: No Fabricated Citations When Evidence Is Absent**
    - **Validates: Requirements 6.7, 7.6**
    - Use Hypothesis to generate questions with all-chunks-below-0.5 score scenarios
    - Mock the Bedrock Converse client
    - Assert `cited_log_ids` is empty and the response text does not contain any log IDs from the index
    - `@settings(max_examples=100)`
    - _Requirements: 6.7, 7.6_

- [ ] 20. Create the evaluation dataset
  - [~] 20.1 Create `eval/questions.json` with exactly 25 evaluation questions
    - Each entry must contain: `question` (natural-language string), `reference_answer` (string), `expected_log_ids` (list of at least one log ID)
    - Include at least 3 questions for database connection timeout, at least 3 for permission errors, and at least 3 for cold-start latency spikes (minimum 9 scenario-specific questions)
    - _Requirements: 7.1, 7.2_

- [ ] 21. Implement the `Evaluation Runner`
  - [~] 21.1 Implement `eval/run_eval.py` as a CLI script
    - Accept `--model-id` argument; exit with a non-zero status code and an error message if the model ID is not one of `amazon.nova-micro-v1:0`, `amazon.nova-lite-v1:0`, `amazon.nova-2-lite-v1:0`
    - For each of the 25 questions: run the full retrieval + RAG pipeline, record retrieved log IDs, answer text, citation-pass/fail, and refusal-pass/fail verdicts
    - Compute recall@8 as the proportion of questions where at least one expected log ID appears in the top 8 retrieved documents
    - Write a JSON result file to `eval/results/` with: UTC timestamp (ISO 8601), model ID, per-question verdicts, recall@8 score
    - _Requirements: 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_
  - [ ]* 21.2 Write property test for recall@8 computation
    - **Property 12: Recall@8 Score Is Correctly Computed**
    - **Validates: Requirement 7.4**
    - Use Hypothesis to generate arbitrary collections of per-question result dicts (each with `retrieved_ids` and `expected_ids` sets)
    - Assert the computed recall@8 equals the proportion of questions where the intersection is non-empty
    - Assert the result is always in `[0.0, 1.0]`
    - `@settings(max_examples=100)`
    - _Requirements: 7.4_

- [~] 22. Phase 3 checkpoint
  - Run `pytest tests/` and confirm retriever, RAG agent, and eval runner tests all pass. Verify manually that a CLI invocation of `eval/run_eval.py --model-id amazon.nova-lite-v1:0` runs without crashing (using synthetic/mocked data). Ask the user if questions arise.

---

### Phase 4 — API Server, Session Memory, and User Interface

- [ ] 23. Implement the FastAPI server and Pydantic schemas
  - [~] 23.1 Implement `api/server.py` with `GET /health` and `POST /chat` endpoints
    - Define `ChatRequest` (Pydantic v2): `session_id` Field(min_length=1, max_length=128), `question` Field(min_length=1, max_length=1000)
    - Define `ChatResponse`: `answer` (str), `cited_log_ids` (List[str], max_length=20), `warning` (str | None)
    - Define `HealthResponse`: `status: str` always `"ok"`
    - `GET /health` returns HTTP 200 with `{"status": "ok"}`
    - `POST /chat` returns HTTP 422 with a validation error body identifying the offending field for out-of-bounds inputs
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.8_
  - [ ]* 23.2 Write property test for API field length validation
    - **Property 11: API Validates Request Field Lengths**
    - **Validates: Requirements 8.3, 8.4**
    - Use Hypothesis and FastAPI `TestClient` to generate `session_id` strings of length outside `[1, 128]` and `question` strings outside `[1, 1000]`
    - Assert HTTP 422 is returned with a validation body identifying the offending field
    - Also assert HTTP 200 is returned when both fields are within bounds
    - `@settings(max_examples=100)`
    - _Requirements: 8.3, 8.4_

- [ ] 24. Implement the `Memory` component with DynamoDB
  - [~] 24.1 Implement `agent/memory.py` — DynamoDB-backed session history
    - Use the table name from SSM `/cloudops/dynamodb/table-name`
    - Table schema: `session_id` (PK, String), `turn_index` (SK, Number), `question`, `answer`, `timestamp` (ISO 8601 UTC)
    - `load_history(session_id)` returns all turns sorted by `turn_index`
    - `save_turn(session_id, question, answer)` appends a new turn; if the session already has 6 turns, delete `turn_index = 0` and re-index remaining turns before appending
    - On DynamoDB read failure: raise a custom `MemoryReadError` that `api/server.py` catches to return HTTP 503
    - On DynamoDB write failure: log the error; do not raise; signal via `warning` field in the response
    - _Requirements: 8.5, 8.6, 8.7, 8.9, 8.10_
  - [ ]* 24.2 Write property test for session memory truncation
    - **Property 7: Session Memory Retains Only the Most Recent Six Turns**
    - **Validates: Requirement 8.6**
    - Use Hypothesis with `moto` DynamoDB to generate sessions with N prior turns (0–20) and add one new turn
    - Assert the session contains exactly `min(N + 1, 6)` turns
    - Assert the retained turns are the chronologically most recent in ascending order
    - `@settings(max_examples=100)`
    - _Requirements: 8.6_
  - [ ]* 24.3 Write unit tests for DynamoDB unavailability handling
    - Mock DynamoDB to raise `ClientError` on read: assert `POST /chat` returns HTTP 503
    - Mock DynamoDB to raise `ClientError` on write: assert `POST /chat` returns HTTP 200 with `warning` field set
    - _Requirements: 8.9, 8.10_

- [ ] 25. Wire `POST /chat` pipeline end-to-end in `api/server.py`
  - [~] 25.1 Connect `Memory`, `Retriever`, and `RAG_Agent` inside the `POST /chat` handler
    - Call `Memory.load_history(session_id)` → pass to `RAG_Agent` as context
    - Call `Retriever.retrieve(question, filters)` → pass chunks to `RAG_Agent`
    - Call `RAG_Agent.answer(question, chunks, history)` → get `answer` and `cited_log_ids`
    - Call `Memory.save_turn(session_id, question, answer)` → set `warning` if it fails
    - Return `ChatResponse`
    - _Requirements: 8.7, 8.10_

- [ ] 26. Implement the Streamlit UI
  - [~] 26.1 Implement `ui/app.py` with a chat interface
    - Generate `session_id` as UUID4 in `st.session_state` on first load
    - Render a text input and a scrollable message history
    - On submission: `POST /chat` to the FastAPI server using `httpx`; display the answer and a collapsible "Citations" section listing `cited_log_ids`
    - _Requirements: 9.1, 9.2, 9.3_

- [ ] 27. Configure Docker Compose for local development
  - [~] 27.1 Write `docker-compose.yml` with two services: `api` and `ui`
    - `api` service: build from project root, expose port 8000, pass `.env` variables
    - `ui` service: build from project root, expose port 8501, set `FASTAPI_URL=http://api:8000`
    - Both services should start from a single `docker-compose up` and be accessible at their respective ports
    - _Requirements: 9.4, 9.5_

- [ ] 28. Write integration tests for the API
  - [~] 28.1 Write integration tests in `tests/test_api.py` using FastAPI `TestClient` and `moto`
    - `GET /health` returns HTTP 200 with `{"status": "ok"}`
    - `POST /chat` with valid body returns a response conforming to `ChatResponse` schema
    - `POST /chat` with missing `session_id` returns HTTP 422
    - `POST /chat` with `question` exceeding 1000 characters returns HTTP 422
    - _Requirements: 9.6_

- [~] 29. Phase 4 checkpoint
  - Run `pytest tests/` and confirm all API, memory, and integration tests pass. Start the application locally with `docker-compose up` and manually verify `/health` and a single `/chat` request. Ask the user if questions arise.

---

### Phase 5 — Containerization and AWS Deployment

- [ ] 30. Write the production Dockerfile
  - [~] 30.1 Implement the production `Dockerfile`
    - Use `python:3.12-slim` as the base image
    - Copy only application source files; do not copy `.env`, credentials, or test files
    - Install dependencies from `pyproject.toml` without dev dependencies
    - Start both the FastAPI server (port 8000) and the Streamlit application (port 8501) using a process manager or `CMD` entrypoint script; both must respond to a health probe within 60 seconds
    - _Requirements: 10.1, 10.2_
  - [ ]* 30.2 Validate container starts within 60 seconds
    - Build the image locally: `docker build -t cloudops-copilot .`
    - Run the container and confirm both ports respond to a health probe before the image is pushed
    - _Requirements: 10.2_

- [ ] 31. Provision ECR and push the image
  - [~] 31.1 Create a private ECR repository named `cloudops-copilot`
    - Tag the image with a version identifier (e.g., `latest` and the current Git commit SHA)
    - Push the image to ECR using `aws ecr get-login-password | docker login` then `docker push`
    - _Requirements: 10.3_

- [ ] 32. Configure IAM instance role with least-privilege permissions
  - [~] 32.1 Create an EC2 IAM instance role
    - Grant: `s3:GetObject` on the specific FAISS index prefix only (not the entire bucket)
    - Grant: `bedrock:InvokeModel` on the three Nova model ARNs and the Titan embedding ARN listed in the project configuration
    - Grant: `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:DeleteItem`, `dynamodb:Query` on the session history table
    - Grant: `ssm:GetParameter` on all parameters under `/cloudops/*`
    - Do not grant any broader permissions
    - _Requirements: 10.4, 16.1, 16.6_

- [ ] 33. Launch and configure the EC2 instance
  - [~] 33.1 Launch an EC2 t3.micro instance
    - Use the default VPC on a public subnet
    - Attach the IAM instance role from Task 32.1
    - Enable IMDSv2 by setting `HttpTokens=required` and `HttpPutResponseHopLimit=1`
    - Encrypt the EBS root volume using the default AWS-managed EBS key
    - Apply the `project=cloudops-copilot` tag
    - _Requirements: 10.5, 10.9, 10.10, 16.2_
  - [~] 33.2 Configure the EC2 security group
    - Allow inbound TCP on ports 8000 and 8501 only from the developer's current public IP as `<IP>/32`
    - Deny all other inbound traffic on those ports
    - Keep port 22 closed
    - _Requirements: 10.6, 16.3_
  - [~] 33.3 Configure SSM Session Manager on the EC2 instance
    - Attach the `AmazonSSMManagedInstanceCore` managed policy to the instance role
    - Verify shell access is available through SSM without opening port 22
    - _Requirements: 10.7, 16.3_

- [ ] 34. Deploy the container and verify the deployment
  - [~] 34.1 Pull the ECR image on the EC2 instance and start the container
    - Log in to ECR from the EC2 instance using the instance role (no credentials stored)
    - Pull the image and start the container with the appropriate environment variables sourced from SSM
    - _Requirements: 10.8_
  - [~] 34.2 Verify deployment health
    - From the permitted `/32` IP: confirm `GET /health` responds with HTTP 200 within 5 seconds
    - Confirm `POST /chat` accepts a request on port 8000 and returns a valid `ChatResponse`
    - _Requirements: 10.8_

- [~] 35. Phase 5 checkpoint
  - Confirm the container is running on EC2, both services respond from the permitted IP, IMDSv2 is enforced, EBS is encrypted, and port 22 is closed. Ask the user if questions arise.

---

### Phase 6 — Automated Log Refresh and Monitoring (Recommended)

- [ ] 36. Implement the `Log Refresher` Lambda
  - [~] 36.1 Implement `lambdas/log_refresher/handler.py`
    - Follow the 9-step write order: read Checkpoint → `CloudWatchPlugin.fetch()` → `Chunker.chunk()` → `Embedder.embed_batch()` → load current FAISS index from S3 → `index.add(new_vectors)` → write new versioned index and metadata to `s3://bucket/index/v{timestamp}/` → update Latest_Pointer → write new Checkpoint
    - When zero new events exist: leave index, Latest_Pointer, and Checkpoint unchanged
    - On any S3 write failure: abort immediately, leave all S3 objects in their pre-run state, return a non-zero exit code
    - _Requirements: 11.1, 11.2, 11.5, 11.9_
  - [~] 36.2 Package FAISS for the Lambda execution environment
    - Bundle a FAISS binary compiled for x86_64 Lambda environment as a Lambda layer (faiss-cpu)
    - Test the Lambda package locally or in a Lambda test execution to confirm FAISS imports correctly
    - _Requirements: 11.3_

- [ ] 37. Schedule the Log Refresher and implement hot-reload
  - [~] 37.1 Create an EventBridge rule to trigger `Log Refresher` every 30 minutes
    - Use a cron expression: `rate(30 minutes)`
    - _Requirements: 11.7_
  - [~] 37.2 Implement background index hot-reload in the EC2 application
    - Start a background thread in `api/server.py` that polls `s3://bucket/index/latest` every 30 seconds
    - When the latest-pointer value changes, download the new index and atomically swap the in-memory `VectorStore` reference without restarting the container process
    - Verify the new index is searchable through the API within 30 seconds of detecting the pointer change
    - _Requirements: 11.6, 11.8_

- [ ] 38. Configure CloudWatch alarms, SNS notifications, and dashboard
  - [~] 38.1 Create CloudWatch alarms for `Log Refresher` errors
    - Alarm on the `Errors` metric for the `log_refresher` Lambda function
    - Configure the alarm to transition to ALARM state after 1 evaluation period with threshold ≥ 1 error
    - _Requirements: 12.1_
  - [~] 38.2 Create an SNS topic and subscribe a verified developer email address
    - Create the SNS topic and confirm the subscription before activating any alarms
    - Connect all CloudWatch alarms to publish to this topic
    - _Requirements: 12.2, 12.5_
  - [~] 38.3 Create a CloudWatch dashboard
    - Include widgets for: `Log Refresher` Lambda invocation count, error count, and duration; EC2 CPU utilization; DynamoDB read/write capacity consumption
    - _Requirements: 12.3_

- [ ] 39. Test forced failure and alarm delivery
  - [~] 39.1 Intentionally force a `Log Refresher` Lambda failure and verify the alarm fires
    - Introduce a deliberate error (e.g., invalid S3 bucket name via SSM parameter), invoke the Lambda manually, confirm the CloudWatch alarm transitions to ALARM, and confirm an SNS email is received
    - Restore the correct SSM parameter value after the test
    - _Requirements: 12.4_

- [~] 40. Phase 6 checkpoint
  - Confirm the Log Refresher Lambda runs successfully on its EventBridge schedule, new logs become searchable without restart, the CloudWatch dashboard is visible, and the alarm email is received on forced failure. Ask the user if questions arise.

---

### Phase 7 — Infrastructure as Code and CI/CD (Recommended)

- [ ] 41. Create the AWS CDK Python application
  - [~] 41.1 Initialize the CDK app in the `infra/` directory
    - Run `cdk init app --language python` in `infra/`
    - Define a single stack `CloudOpsCopilotStack` in `infra/cloud_ops_copilot/stack.py`
    - Apply the `project=cloudops-copilot` tag to all resources using `Tags.of(stack).add()`
    - _Requirements: 13.1, 13.6_

- [ ] 42. Implement CDK constructs for storage, ECR, and configuration
  - [~] 42.1 Implement `StorageConstruct`
    - S3 bucket: versioning enabled (`BucketVersioning.ENABLED`), all public access blocked, `RemovalPolicy.RETAIN`
    - DynamoDB table: on-demand billing, `RemovalPolicy.RETAIN`, encryption at rest using AWS-managed key
    - _Requirements: 13.2, 13.5, 13.7_
  - [~] 42.2 Implement `ContainerConstruct` and `ConfigConstruct`
    - ECR repository with `RemovalPolicy.DESTROY` (images are rebuildable)
    - SSM String parameters for all `/cloudops/*` paths
    - _Requirements: 13.2_

- [ ] 43. Implement CDK constructs for compute and Lambda
  - [~] 43.1 Implement `ComputeConstruct`
    - EC2 t3.micro instance with IMDSv2 enforced, encrypted EBS volume, IAM instance profile (least-privilege role from Task 32.1), security group (ports 8000/8501 open to `/32` CIDR only, port 22 closed)
    - _Requirements: 13.2_
  - [~] 43.2 Implement `LambdaConstruct`
    - `log_generator` function: 128 MB memory, 60 s timeout, EventBridge trigger every 5 min, least-privilege execution role
    - `log_refresher` function: 512 MB memory, 300 s timeout, FAISS layer, EventBridge trigger every 30 min, least-privilege execution role
    - _Requirements: 13.2, 16.7_

- [ ] 44. Implement CDK constructs for scheduling and observability
  - [~] 44.1 Implement `ScheduleConstruct` and `ObservabilityConstruct`
    - `ScheduleConstruct`: EventBridge rules for 5-min log generator and 30-min log refresher
    - `ObservabilityConstruct`: CloudWatch alarms, SNS topic, CloudWatch dashboard
    - _Requirements: 13.2_

- [ ] 45. Validate CDK synthesis and deploy
  - [~] 45.1 Run `cdk synth` and confirm zero-exit with valid CloudFormation template
    - Write a CDK stack assertion test in `tests/test_infra.py` using `aws_cdk.assertions` to snapshot the synthesized template
    - _Requirements: 13.3_
  - [~] 45.2 Deploy the CDK stack and verify all resources
    - Run `cdk deploy` and confirm all resources are created and operational within 30 minutes
    - _Requirements: 13.4_

- [ ] 46. Migrate hand-built resources to CDK management
  - [~] 46.1 Inventory and safely remove hand-built resources replaced by CDK
    - Document the record count in DynamoDB and the object count in S3 before removal
    - Remove hand-built resources (EC2, security group, IAM role, Lambda functions, EventBridge rules, CloudWatch alarms, SNS topic) once CDK-managed equivalents are running
    - Verify record count equality in DynamoDB and S3 after migration; confirm no more than 10 minutes of service unavailability per resource group
    - _Requirements: 13.8_

- [ ] 47. Configure GitHub Actions CI pipeline
  - [~] 47.1 Create `.github/workflows/ci.yml`
    - Trigger on `push` and `pull_request` events
    - Run `pytest` test suite and publish the result as a GitHub commit status check
    - On `pull_request`: run `pytest` only; do not trigger any deployment steps
    - _Requirements: 14.1, 14.6_
  - [~] 47.2 Configure GitHub OIDC federation with AWS
    - Create an IAM OIDC identity provider for `token.actions.githubusercontent.com` in the AWS account
    - Create an IAM role trusted by the OIDC provider, scoped to the `cloudops-copilot` repository
    - Grant only the permissions needed: ECR push, SSM Run Command on the target EC2 instance
    - Store the IAM role ARN as a GitHub Actions variable (not a secret)
    - Confirm no long-lived AWS access keys are stored anywhere in the repository or GitHub Actions secrets
    - _Requirements: 14.2, 14.5_
  - [~] 47.3 Add Docker build, ECR push, and SSM deploy steps to CI
    - On `push` to `main` after `pytest` passes: build the production Docker image, tag it with the full Git commit SHA, push to ECR
    - After successful ECR push: issue an SSM Run Command to the EC2 instance to pull the new image and restart the container; fail the workflow step if the command does not complete within 300 seconds
    - _Requirements: 14.3, 14.4_

- [~] 48. Phase 7 checkpoint
  - Run `cdk synth` (exits zero), run `pytest tests/test_infra.py` (snapshot passes), push to `main` and confirm the full CI pipeline runs end-to-end (pytest → Docker build → ECR push → SSM deploy). Ask the user if questions arise.

---

### Phase 8 — Final Integration, Portfolio Delivery, and Teardown

- [ ] 49. Run end-to-end validation
  - [~] 49.1 Execute the complete end-to-end integration test
    - Trigger the `Log Generator` Lambda to produce new synthetic logs
    - Trigger the `Log Refresher` Lambda to ingest, embed, and index the new logs
    - Confirm via the Streamlit UI that the new records are searchable (ask a question referencing a recently generated log)
    - Confirm the API returns at least one citation matching a log ID from the current run
    - _Requirements: 15.1_

- [ ] 50. Implement the optional `S3AccessLogPlugin`
  - [~] 50.1 Implement `plugins/s3_access_plugin.py` (optional)
    - Implement `LogPlugin` for S3 server access logs using the documented S3 server access log format
    - Parse each access log line into a `LogRecord` object
    - _Requirements: 15.9, 15.10_

- [ ] 51. Run the final evaluation and produce the results table
  - [~] 51.1 Run `eval/run_eval.py` against all three models
    - Execute `python eval/run_eval.py --model-id amazon.nova-micro-v1:0`, `--model-id amazon.nova-lite-v1:0`, and `--model-id amazon.nova-2-lite-v1:0`
    - Produce a final results table in `eval/results/` comparing recall@8, citation accuracy, and refusal rate across all three models
    - _Requirements: 15.2_

- [ ] 52. Write portfolio documentation
  - [~] 52.1 Complete the root `README.md`
    - Include: project description, architecture diagram (Mermaid or image file), cost breakdown for the 14-day run, setup instructions, teardown instructions, evaluation results summary
    - _Requirements: 15.3, 15.4_
  - [~] 52.2 Add the architecture diagram
    - Create or embed a diagram accurately representing all AWS services and data flow (consistent with the Mermaid diagram in `design.md`)
    - _Requirements: 15.4_

- [ ] 53. Perform security review
  - [~] 53.1 Review IAM permissions, sample data, and exposed ports
    - Confirm no real customer or personal data is ingested
    - Confirm IAM roles use least privilege
    - Confirm port 22 is closed and only the developer's `/32` CIDR can reach ports 8000/8501
    - _Requirements: 16.8, 15.7_

- [ ] 54. Teardown and final verification
  - [~] 54.1 Run `cdk destroy` to remove all billable resources
    - Confirm the EC2 instance, EBS volume, Elastic IP, Lambda functions, and EventBridge rules are removed
    - Confirm S3 objects and DynamoDB data are retained per the `RemovalPolicy.RETAIN` configuration
    - Manually delete S3 objects and ECR images if removing them completely
    - _Requirements: 15.6, 13.5_
  - [~] 54.2 Verify no remaining tagged resources
    - Use Tag Editor to search for `project=cloudops-copilot` and confirm zero results
    - Check the AWS Billing console the following day to confirm no new charges are accruing
    - _Requirements: 15.7, 15.8_

- [~] 55. Final checkpoint
  - Confirm end-to-end test passes, evaluation results are written, README is complete, teardown is verified, and no billable resources remain. Ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP, but recommended for production confidence.
- **Required (core application):** Phases 0–5 (Tasks 1–35) and Phase 8 (Tasks 49–55).
- **Recommended (strong portfolio):** Phase 6 (Tasks 36–40) and Phase 7 (Tasks 41–48).
- **Optional:** Task 50.1 (S3AccessLogPlugin).
- Property tests use [Hypothesis](https://hypothesis.readthedocs.io/) with `@settings(max_examples=100)`.
- Unit tests use [moto](https://docs.getmoto.org/) for all AWS API mocking — no real AWS calls in tests.
- The write order in Task 36.1 (faiss.index → metadata.json → latest pointer → checkpoint) is intentional: a crash between pointer update and checkpoint write causes a small re-processing window on the next run, which deduplication handles safely.
- The FAISS binary (Task 36.2) must be compiled for the Lambda's CPU architecture. Use `faiss-cpu` from a Lambda-compatible build or a pre-built Lambda layer (e.g., from the `lambda-faiss-python` community project).
- All AWS access from EC2 and Lambda uses IAM roles; no long-lived access keys are stored anywhere.

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["2.1", "3.1", "4.1"] },
    { "id": 1, "tasks": ["2.2", "3.2", "4.2", "5.1", "7.1"] },
    { "id": 2, "tasks": ["5.2", "7.2", "8.1", "9.1"] },
    { "id": 3, "tasks": ["8.2", "9.2", "10.1", "11.1"] },
    { "id": 4, "tasks": ["10.2", "10.3", "10.4", "11.2", "13.1"] },
    { "id": 5, "tasks": ["13.2", "14.1", "15.1", "16.1"] },
    { "id": 6, "tasks": ["13.3", "14.2", "15.2", "16.2"] },
    { "id": 7, "tasks": ["16.3", "16.4", "18.1"] },
    { "id": 8, "tasks": ["18.2", "19.1"] },
    { "id": 9, "tasks": ["19.2", "19.3", "20.1", "21.1"] },
    { "id": 10, "tasks": ["21.2", "23.1", "24.1"] },
    { "id": 11, "tasks": ["23.2", "24.2", "24.3", "25.1"] },
    { "id": 12, "tasks": ["26.1", "28.1"] },
    { "id": 13, "tasks": ["27.1", "30.1"] },
    { "id": 14, "tasks": ["30.2", "31.1"] },
    { "id": 15, "tasks": ["32.1", "33.1"] },
    { "id": 16, "tasks": ["33.2", "33.3", "34.1"] },
    { "id": 17, "tasks": ["34.2", "36.1"] },
    { "id": 18, "tasks": ["36.2", "37.1"] },
    { "id": 19, "tasks": ["37.2", "38.1"] },
    { "id": 20, "tasks": ["38.2", "38.3"] },
    { "id": 21, "tasks": ["39.1", "41.1"] },
    { "id": 22, "tasks": ["42.1", "42.2"] },
    { "id": 23, "tasks": ["43.1", "43.2"] },
    { "id": 24, "tasks": ["44.1"] },
    { "id": 25, "tasks": ["45.1"] },
    { "id": 26, "tasks": ["45.2", "47.1"] },
    { "id": 27, "tasks": ["46.1", "47.2"] },
    { "id": 28, "tasks": ["47.3"] },
    { "id": 29, "tasks": ["49.1", "50.1"] },
    { "id": 30, "tasks": ["51.1"] },
    { "id": 31, "tasks": ["52.1", "52.2", "53.1"] },
    { "id": 32, "tasks": ["54.1"] },
    { "id": 33, "tasks": ["54.2"] }
  ]
}
```
