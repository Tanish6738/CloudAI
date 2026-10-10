# Phase 5 Quick Reference - AWS Deployment

**Goal**: Deploy to AWS in 3 hours  
**Cost**: ~$5-10  
**Status**: Ready to start

---

## Pre-Flight Checklist

- [ ] AWS CLI configured: `aws sts get-caller-identity`
- [ ] Docker installed: `docker --version`
- [ ] Get your account ID: `aws sts get-caller-identity --query Account --output text`
- [ ] Get your public IP: `curl ifconfig.me`
- [ ] Tests passing: `pytest tests/ -v`

---

## 9 AWS Services (What They Do)

| Service | What It Is | What We Use It For | Cost |
|---------|-----------|-------------------|------|
| **EC2** | Virtual computer | Run FastAPI + Streamlit | $3.50 |
| **S3** | Cloud storage | Store FAISS indices | $0.01 |
| **DynamoDB** | Cloud database | Store chat history | $0 |
| **CloudWatch** | Log storage | Store app logs | $0 |
| **Lambda** | Serverless code | Run every 5 min | $0 |
| **EventBridge** | Scheduler | Trigger Lambda | $0 |
| **Bedrock** | AI models | Embeddings + LLM | $1-2 |
| **IAM** | Permissions | Grant EC2 access | $0 |
| **ECR** | Docker storage | Store app image | $0 |

---

## 10 Deployment Steps

### Step 1: Create S3 Bucket (2 min)

```powershell
# Set your account ID
$ACCOUNT_ID = "YOUR_ACCOUNT_ID"

aws s3 mb s3://cloudops-copilot-index-$ACCOUNT_ID --region us-east-1

# Verify
aws s3 ls | grep cloudops-copilot
```

---

### Step 2: Create DynamoDB Table (2 min)

```powershell
aws dynamodb create-table `
  --table-name cloudops-chat-history `
  --attribute-definitions AttributeName=session_id,AttributeType=S AttributeName=turn_index,AttributeType=N `
  --key-schema AttributeName=session_id,KeyType=HASH AttributeName=turn_index,KeyType=RANGE `
  --billing-mode PAY_PER_REQUEST `
  --region us-east-1

# Verify
aws dynamodb list-tables --region us-east-1
```

---

### Step 3: Create CloudWatch Log Group (1 min)

```powershell
aws logs create-log-group `
  --log-group-name /cloudops-copilot/app `
  --region us-east-1

# Verify
aws logs describe-log-groups --region us-east-1
```

---

### Step 4: Create IAM Role (5 min)

**Save as trust-policy.json:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Create role:**
```powershell
aws iam create-role `
  --role-name cloudops-copilot-ec2-role `
  --assume-role-policy-document file://trust-policy.json
```

**Save as ec2-permissions.json:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::cloudops-copilot-index-*", "arn:aws:s3:::cloudops-copilot-index-*/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query", "dynamodb:Scan"],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/cloudops-chat-history"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams", "logs:GetLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:*:log-group:/cloudops-copilot/app:*"
    },
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "*"
    }
  ]
}
```

**Attach permissions:**
```powershell
aws iam put-role-policy `
  --role-name cloudops-copilot-ec2-role `
  --policy-name cloudops-ec2-permissions `
  --policy-document file://ec2-permissions.json

# Create instance profile
aws iam create-instance-profile `
  --instance-profile-name cloudops-copilot-ec2-profile

aws iam add-role-to-instance-profile `
  --instance-profile-name cloudops-copilot-ec2-profile `
  --role-name cloudops-copilot-ec2-role
```

---

### Step 5: Create Security Group (3 min)

```powershell
# Create security group
$SG_ID = aws ec2 create-security-group `
  --group-name cloudops-copilot-sg `
  --description "Cloud Ops Copilot app" `
  --region us-east-1 `
  --query 'GroupId' `
  --output text

# Get your IP (from curl ifconfig.me)
$YOUR_IP = "YOUR_PUBLIC_IP"

# Allow API port 8000
aws ec2 authorize-security-group-ingress `
  --group-id $SG_ID `
  --protocol tcp `
  --port 8000 `
  --cidr "$YOUR_IP/32" `
  --region us-east-1

# Allow Streamlit port 8501
aws ec2 authorize-security-group-ingress `
  --group-id $SG_ID `
  --protocol tcp `
  --port 8501 `
  --cidr "$YOUR_IP/32" `
  --region us-east-1

Write-Host "Security Group ID: $SG_ID"
```

---

### Step 6: Launch EC2 Instance (3 min)

```powershell
$ACCOUNT_ID = "YOUR_ACCOUNT_ID"
$SG_ID = "sg-xxxxxxxx"  # From previous step

$INSTANCE_ID = aws ec2 run-instances `
  --image-id ami-0c55b159cbfafe1f0 `
  --instance-type t3.micro `
  --iam-instance-profile Name=cloudops-copilot-ec2-profile `
  --security-group-ids $SG_ID `
  --region us-east-1 `
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=cloudops-copilot},{Key=project,Value=cloudops-copilot}]' `
  --query 'Instances[0].InstanceId' `
  --output text

Write-Host "Instance ID: $INSTANCE_ID"

# Wait 30 seconds
Start-Sleep -Seconds 30

# Get public IP
$PUBLIC_IP = aws ec2 describe-instances `
  --instance-ids $INSTANCE_ID `
  --region us-east-1 `
  --query 'Reservations[0].Instances[0].PublicIpAddress' `
  --output text

Write-Host "Public IP: $PUBLIC_IP"
```

---

### Step 7: Create ECR Repository (2 min)

```powershell
aws ecr create-repository `
  --repository-name cloudops-copilot `
  --region us-east-1

# Get ECR URI
$ECR_URI = aws ecr describe-repositories `
  --repository-names cloudops-copilot `
  --region us-east-1 `
  --query 'repositories[0].repositoryUri' `
  --output text

Write-Host "ECR URI: $ECR_URI"
```

---

### Step 8: Build & Push Docker Image (5 min)

```powershell
cd c:\Users\ASUS\Desktop\CloudAI\cloudops-copilot

# Build image
docker build -t cloudops-copilot:latest .

# Tag image
docker tag cloudops-copilot:latest $ECR_URI:latest

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URI

# Push to ECR
docker push $ECR_URI:latest

Write-Host "Docker image pushed successfully!"
```

---

### Step 9: Deploy Container to EC2 (10 min)

**Connect to EC2:**
```powershell
$INSTANCE_ID = "i-xxxxxxxx"

aws ssm start-session --target $INSTANCE_ID --region us-east-1
```

**Inside EC2 (copy-paste one by one):**

```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install docker -y
sudo systemctl start docker
sudo usermod -a -G docker ec2-user

# Exit and reconnect
exit

# (Reconnect with: aws ssm start-session --target i-xxxxx --region us-east-1)

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Pull image
docker pull YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cloudops-copilot:latest

# Run container
docker run -d \
  -p 8000:8000 \
  -p 8501:8501 \
  -e AWS_REGION=us-east-1 \
  -e FASTAPI_HOST=0.0.0.0 \
  -e FASTAPI_PORT=8000 \
  -e STREAMLIT_PORT=8501 \
  --name cloudops-copilot \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cloudops-copilot:latest

# Verify running
docker ps
```

---

### Step 10: Test Deployment (5 min)

```powershell
# Test API health
curl http://YOUR_EC2_PUBLIC_IP:8000/health

# Expected: {"status":"ok"}

# Test chat endpoint
$body = @{
    session_id = "test-session"
    question = "What happened?"
} | ConvertTo-Json

curl -X POST http://YOUR_EC2_PUBLIC_IP:8000/chat `
  -H "Content-Type: application/json" `
  -d $body

# Open Streamlit UI in browser
start "http://YOUR_EC2_PUBLIC_IP:8501"
```

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| "Permission denied" | Verify IAM role attached to EC2 |
| "Cannot connect" | Check security group allows your IP |
| "Docker not found" | Install Docker: `sudo yum install docker -y` |
| "S3 bucket exists" | Bucket names must be globally unique |
| "DynamoDB ResourceInUseException" | Table name already taken, use different name |
| "Bedrock access denied" | Verify your IAM user has Bedrock access |

---

## Cost Verification

```powershell
# Check current spend
aws ce get-cost-and-usage `
  --time-period Start=2026-01-01,End=2026-12-31 `
  --granularity MONTHLY `
  --metrics "UnblendedCost" `
  --group-by Type=DIMENSION,Key=SERVICE `
  --region us-east-1
```

Expected: **$0-5**

---

## Cleanup (When Done)

```powershell
# Stop EC2 instance
aws ec2 stop-instances --instance-ids $INSTANCE_ID --region us-east-1

# Terminate EC2 instance (to stop paying)
aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region us-east-1

# Delete S3 bucket (after terminating EC2)
aws s3 rb s3://cloudops-copilot-index-$ACCOUNT_ID --force

# Delete DynamoDB table
aws dynamodb delete-table --table-name cloudops-chat-history --region us-east-1

# Delete CloudWatch log group
aws logs delete-log-group --log-group-name /cloudops-copilot/app --region us-east-1

# Delete IAM resources
aws iam remove-role-from-instance-profile `
  --instance-profile-name cloudops-copilot-ec2-profile `
  --role-name cloudops-copilot-ec2-role

aws iam delete-instance-profile --instance-profile-name cloudops-copilot-ec2-profile

aws iam delete-role-policy `
  --role-name cloudops-copilot-ec2-role `
  --policy-name cloudops-ec2-permissions

aws iam delete-role --role-name cloudops-copilot-ec2-role

# Delete security group (wait 5 min after terminating EC2)
Start-Sleep -Seconds 300
aws ec2 delete-security-group --group-id $SG_ID --region us-east-1

# Delete ECR repository
aws ecr delete-repository --repository-name cloudops-copilot --force --region us-east-1
```

---

## Success Checklist

After Phase 5, you should have:

- [ ] S3 bucket created
- [ ] DynamoDB table created
- [ ] CloudWatch log group created
- [ ] IAM role with permissions
- [ ] Security group configured
- [ ] EC2 instance running
- [ ] Docker image in ECR
- [ ] Container running on EC2
- [ ] API responding at `/health`
- [ ] Chat endpoint working
- [ ] Streamlit UI accessible
- [ ] Real Bedrock integration working

---

## Quick Commands Summary

```powershell
# Get account ID
aws sts get-caller-identity --query Account --output text

# List S3 buckets
aws s3 ls

# List DynamoDB tables
aws dynamodb list-tables --region us-east-1

# List EC2 instances
aws ec2 describe-instances --region us-east-1

# List ECR repositories
aws ecr describe-repositories --region us-east-1

# Connect to EC2
aws ssm start-session --target i-xxxxxxxx --region us-east-1

# View docker logs
docker logs cloudops-copilot

# Stop container
docker stop cloudops-copilot

# Restart container
docker restart cloudops-copilot
```

---

## Total Timeline

| Step | Time | What You Do |
|------|------|-----------|
| 1-3 | 5 min | Create storage & databases |
| 4-5 | 8 min | Create security |
| 6 | 3 min | Launch EC2 |
| 7-8 | 7 min | Push Docker image |
| 9 | 10 min | Deploy container |
| 10 | 5 min | Test |
| **TOTAL** | **~40 min** | **Deployment complete!** |

---

## What Happens After Deployment

✅ Your app runs 24/7 on EC2  
✅ Users can access it from browser  
✅ Bedrock AI answers questions based on real logs  
✅ Chat history saved in DynamoDB  
✅ FAISS indices stored in S3  
✅ Lambda refreshes logs every 5 min  
✅ Cost: ~$5-10 per 2 weeks

---

## Next Steps

1. ✅ Follow steps 1-10 above
2. → Test at `http://YOUR_IP:8501`
3. → Run evaluation: `python eval/run_eval.py --model-id amazon.nova-lite-v1:0`
4. → Cleanup when done (run cleanup commands above)

