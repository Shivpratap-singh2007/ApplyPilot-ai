# Installation Guide (Windows 10/11)

## 1. Prerequisites
- **Python 3.12** (`python --version`)
- **Node.js 20+** and **npm** (`node --version`, `npm --version`)
- **Git**
- **Ollama** installed locally from https://ollama.com/download

## 2. Pull Local Qwen3 Models
For 16 GB RAM laptops (quantized default):
```powershell
ollama pull qwen3:4b
```
For lower-resource laptops (optional fallback):
```powershell
ollama pull qwen3:1.7b
```

## 3. Configure Environment
```powershell
Copy-Item .env.example .env
```

## 4. Install Dependencies & Migrate Database
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -r agent\requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\scripts\migrate.ps1
npm --prefix frontend install
npm --prefix frontend run build
```

## 5. Run Locally
Open two PowerShell terminals:
```powershell
.\scripts\start-backend.ps1
```
```powershell
.\scripts\start-frontend.ps1
```
Then visit http://localhost:3000.

