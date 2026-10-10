# Cloud Ops Copilot

RAG-based chat assistant for AWS CloudWatch logs. Answers natural language questions about why Lambda functions failed, timeouts occurred, or permission errors happened.

## Project Status

🚀 **In Development** — Phases 0-1 (Days 0-2) active

## Architecture

- **Frontend**: Streamlit UI (:8501)
- **Backend**: FastAPI server (:8000)
- **RAG Pipeline**: Bedrock (Nova Lite + Titan Embeddings v2) → FAISS → S3
- **Infrastructure**: EC2 t3.micro, Lambda, EventBridge, CDK (Python)
- **Budget**: AWS Free Tier + $100 credits (~$8-10 for 14 days)

## Quick Start

### Prerequisites
- Python 3.12+
- Docker 24.x+
- AWS CLI v2
- Node.js 18+
- CDK CLI 2.x

### Setup
```bash
git clone https://github.com/yourusername/cloudops-copilot.git
cd cloudops-copilot
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

### Run Locally
```bash
docker-compose up
```
Then open http://localhost:8501 for the UI and http://localhost:8000/docs for API docs.

### Run Tests
```bash
pytest tests/
```

## Development Phases

- Phase 0: Environment setup ✓
- Phase 1: Log ingestion (in progress)
- Phase 2: Chunking & embeddings
- Phase 3: Retrieval & RAG
- Phase 4: API & UI
- Phase 5: AWS deployment
- Phase 6: Automated refresh
- Phase 7: CDK & CI/CD
- Phase 8: Final delivery

## Security

- No credentials stored on EC2/Lambda (IAM roles only)
- IMDSv2 enforced
- S3 public access blocked
- EBS encryption enabled
- Least-privilege IAM roles

## License

MIT
