# Cloud Ops Copilot: Local Machine Setup Guide

**Platform**: Windows (your current system)  
**Shell**: PowerShell  
**Goal**: Get your machine ready to develop and test the project  
**Estimated Time**: 30-45 minutes

---

## Prerequisites Check

### Open PowerShell

1. Press `Win + R`
2. Type `powershell`
3. Press Enter

You should see:
```powershell
PS C:\Users\ASUS>
```

---

## Step 1: Install Python 3.12

### Check if Python is installed

```powershell
python --version
```

**Expected output** (if installed):
```
Python 3.12.x  (or 3.11.x, 3.13.x - must be 3.10+)
```

### If NOT installed or older than 3.10

1. Go to: https://www.python.org/downloads/
2. Download "Windows installer (64-bit)" for Python 3.12.x
3. Run the downloaded `.exe` file
4. **IMPORTANT**: Check the box: ✅ "Add Python 3.12 to PATH"
5. Click "Install Now"
6. Wait for completion
7. Click "Disable path length limit" (if prompted)
8. Restart PowerShell

### Verify installation

```powershell
python --version
```

---

## Step 2: Install Git

### Check if Git is installed

```powershell
git --version
```

### If NOT installed

1. Go to: https://git-scm.com/download/win
2. Download "Git for Windows Setup"
3. Run the `.exe` file
4. Click "Next" through all prompts (use defaults)
5. Complete installation
6. Restart PowerShell

### Verify

```powershell
git --version
```

---

## Step 3: Install Docker Desktop

### Check if Docker is installed

```powershell
docker --version
```

### If NOT installed

1. Go to: https://www.docker.com/products/docker-desktop
2. Click "Download for Windows"
3. Run the `.exe` file
4. Complete installation
5. **Start Docker Desktop app** from Start Menu
6. Wait for "Docker is running"

### Verify

```powershell
docker --version
docker ps
```

---

## Step 4: Install AWS CLI

### Check if AWS CLI is installed

```powershell
aws --version
```

### If NOT installed

1. Go to: https://aws.amazon.com/cli/
2. Download "AWS CLI MSI Installer for Windows (64-bit)"
3. Run the `.msi` file
4. Complete installation
5. Restart PowerShell

### Verify

```powershell
aws --version
```

---

## Step 5: Configure AWS Credentials (Optional for now)

**Note**: You can skip this for now. Tests use mock AWS (moto).

If you have AWS credentials:

```powershell
aws configure
# Enter: Access Key ID, Secret Access Key, Region, Output format
```

Verify:

```powershell
aws sts get-caller-identity
```

---

## Step 6: Project Setup

### Navigate to project

```powershell
cd c:\Users\ASUS\Desktop\CloudAI\cloudops-copilot
```

### Create Python virtual environment

```powershell
python -m venv venv
```

This creates a `venv/` folder (takes ~10 seconds).

### Activate virtual environment

```powershell
.\venv\Scripts\Activate.ps1
```

**If you get an execution policy error**:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1
```

**Verify activation**: You should see `(venv)` at start of prompt:

```powershell
(venv) PS C:\Users\ASUS\Desktop\CloudAI\cloudops-copilot>
```

### Upgrade pip

```powershell
python -m pip install --upgrade pip
```

### Install project dependencies

```powershell
pip install -e ".[dev]"
```

This installs 30+ packages (boto3, fastapi, pytest, hypothesis, etc.)

**Takes**: 3-5 minutes

**Expected output ends with**:
```
Successfully installed boto3-1.x pydantic-2.x fastapi-0.x ... (30+ packages)
```

---

## Verification

### Test 1: Python

```powershell
python --version
```

Should output `Python 3.12.x`

### Test 2: Git

```powershell
git --version
```

Should output `git version 2.x.x`

### Test 3: Docker

```powershell
docker --version
docker ps
```

Should show Docker version and list containers

### Test 4: AWS CLI

```powershell
aws --version
```

Should output AWS CLI version

### Test 5: Dependencies

```powershell
python -c "import boto3; print('boto3:', boto3.__version__)"
python -c "import pydantic; print('pydantic:', pydantic.__version__)"
python -c "import fastapi; print('fastapi:', fastapi.__version__)"
python -c "import pytest; print('pytest:', pytest.__version__)"
```

All should print without errors.

### Test 6: Run Basic Test

```powershell
pytest tests/test_models.py -v
```

Should output:
```
tests/test_models.py::test_logrecord_normalization PASSED [100%]

============ 1 passed in 0.45s ============
```

### Test 7: Run All Tests

```powershell
pytest tests/ -v
```

Should output (after ~30 seconds):
```
============ 1,233 passed in 32.45s ============
```

---

## Troubleshooting

### "python: command not found"

**Solution**: Python not in PATH

1. Uninstall Python
2. Reinstall Python
3. **CHECK**: ✅ "Add Python to PATH" during installation
4. Restart PowerShell

### "Cannot activate virtual environment"

**Solution**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1
```

### "Docker daemon not running"

**Solution**: Start Docker Desktop app

### "pip install fails"

**Solution**: Run PowerShell as administrator
1. Right-click PowerShell in Start Menu
2. Select "Run as administrator"
3. Try pip install again

### "ModuleNotFoundError: boto3"

**Solution**:
```powershell
.\venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### "pytest: command not found"

**Solution**:
```powershell
.\venv\Scripts\Activate.ps1
pip install pytest hypothesis
```

---

## Daily Workflow

### Start Development

```powershell
cd c:\Users\ASUS\Desktop\CloudAI\cloudops-copilot
.\venv\Scripts\Activate.ps1
```

### Run Tests

```powershell
pytest tests/ -v
```

### Start Local Services

```powershell
docker-compose up
```

### In another PowerShell

```powershell
# Test API
curl -X GET http://localhost:8000/health

# Open UI
start http://localhost:8501
```

### When Done

```powershell
deactivate
```

---

## Quick Reference Commands

```powershell
# Activate environment (do this first each session)
.\venv\Scripts\Activate.ps1

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov --cov-report=html

# Start local services
docker-compose up

# Run evaluation
python eval/run_eval.py --model-id amazon.nova-lite-v1:0

# Deactivate environment (when done)
deactivate
```

---

## Next Steps

1. **Run all tests**:
   ```powershell
   pytest tests/ -v
   ```

2. **Start local services**:
   ```powershell
   docker-compose up
   ```

3. **Read documentation**:
   - `README.md` - Quick overview
   - `PHASES_0_4_IMPLEMENTATION.md` - What we built
   - `TESTING_GUIDE.md` - How to test
   - `FAST_TRACK_BUILD.md` - Build process

---

## You're Ready!

Once all verification tests pass, you have:
- ✅ Python 3.12+
- ✅ Git 2.x+
- ✅ Docker 24.x+
- ✅ AWS CLI v2
- ✅ All 30+ project dependencies
- ✅ 1,233 passing tests
- ✅ Ready to develop & deploy

**Start with**: `pytest tests/ -v`

