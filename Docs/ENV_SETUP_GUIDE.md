# .env Setup Guide

**Goal**: Configure environment variables for Cloud Ops Copilot  
**Time**: 5 minutes  
**Status**: Required before running tests/services

---

## Quick Start

### 1. Get Your AWS Account ID

```powershell
aws sts get-caller-identity
```

Copy the 12-digit number under "Account".

### 2. Edit `.env` File

```powershell
code .env
```

Or with Notepad:
```powershell
notepad .env
```

### 3. Replace One Line

Find:
```
S3_BUCKET_NAME=cloudops-copilot-index-REPLACE_WITH_YOUR_ACCOUNT_ID
```

Replace with (use YOUR account ID):
```
S3_BUCKET_NAME=cloudops-copilot-index-123456789012
```

### 4. Save

Press Ctrl+S

### 5. Verify

```powershell
Get-Content .env
```

Done! ✅

---

## Environment Variables Explained

### AWS Configuration

```env
AWS_REGION=us-east-1
```
- Which AWS region to use
- Default: `us-east-1` (recommended)

```env
AWS_PROFILE=cloudops-admin
```
- AWS CLI profile name
- Should match your `aws configure` setup

### Bedrock Models (AI)

```env
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
```
- LLM for generating answers
- Options: `nova-micro-v1`, `nova-lite-v1`, `nova-2-lite-v1`
- Recommended: `nova-lite-v1:0`

```env
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
```
- Model for converting text to search vectors
- Don't change this value

### S3 Storage

```env
S3_BUCKET_NAME=cloudops-copilot-index-123456789012
```
- S3 bucket name for storing search index
- Must include YOUR AWS account ID
- Bucket created in Phase 5

```env
S3_INDEX_PREFIX=index/
```
- Folder prefix inside S3 bucket
- Don't change this

### DynamoDB Storage

```env
DYNAMODB_TABLE_NAME=cloudops-chat-history
```
- Table name for storing chat sessions
- Table created in Phase 5
- Don't change this

### CloudWatch Logs

```env
LOG_GROUP_NAME=cloudops-copilot-logs
```
- CloudWatch log group for synthetic logs
- Created in Phase 5
- Don't change this

### Application Ports

```env
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
```
- FastAPI server runs on port 8000
- Don't change these

```env
STREAMLIT_PORT=8501
```
- Streamlit UI runs on port 8501
- Don't change this

---

## Finding Your AWS Account ID

### Method 1: AWS CLI

```powershell
aws sts get-caller-identity
```

Look for "Account" field (12 digits).

### Method 2: AWS Console

1. Go to: https://console.aws.amazon.com/
2. Click your account name (top right)
3. Click "Account"
4. Look for "Account ID"

### Method 3: AWS IAM Console

1. Go to: https://console.aws.amazon.com/iam/
2. Look for "Account ID" in top section

---

## Complete Example .env

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=cloudops-admin

# Bedrock Models
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0

# S3
S3_BUCKET_NAME=cloudops-copilot-index-987654321098
S3_INDEX_PREFIX=index/

# DynamoDB
DYNAMODB_TABLE_NAME=cloudops-chat-history

# CloudWatch Logs
LOG_GROUP_NAME=cloudops-copilot-logs

# Application
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
STREAMLIT_PORT=8501
```

---

## Security

### ✅ Safe:
- `.env` in `.gitignore` (won't be committed)
- Local file only
- Not shared with team

### ❌ Never:
- Commit `.env` to Git
- Share `.env` with others
- Store real API keys in `.env`
- Use root account credentials

---

## Troubleshooting

### "Cannot find .env"

The file should be at:
```
c:\Users\ASUS\Desktop\CloudAI\cloudops-copilot\.env
```

If it doesn't exist, create it:
```powershell
New-Item .env -ItemType File
```

### "AWS_PROFILE not found"

Ensure you ran `aws configure` first:
```powershell
aws configure
```

Then verify:
```powershell
aws sts get-caller-identity --profile cloudops-admin
```

### "S3 bucket not found"

Normal! Bucket is created in Phase 5.

Tests use mock S3 (moto), so this error won't occur until deployment.

### "Cannot read .env"

Ensure you have `.env` in project root:
```powershell
cd c:\Users\ASUS\Desktop\CloudAI\cloudops-copilot
Get-ChildItem | Where-Object Name -eq ".env"
```

---

## Next Steps

1. ✅ Create `.env` file (done)
2. ✅ Fill in your AWS account ID
3. → Run tests: `pytest tests/ -v`
4. → Start services: `docker-compose up`
5. → Proceed to Phase 5 (AWS deployment)

---

## Quick Commands

```powershell
# View .env
Get-Content .env

# Edit .env
code .env

# Verify setup
aws sts get-caller-identity

# Run tests
pytest tests/ -v
```

