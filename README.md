# Procurement Workflow Copilot

A highly autonomous, multi-agent AI copilot designed to streamline and automate corporate procurement workflows. 
Powered by **LangGraph**, **Groq (Llama-3)**, and **Supabase**, this system acts as a team of specialized AI agents that collaborate to process purchase requests, search for products, evaluate vendors, enforce company policies, check budgets, and prepare final summaries for human review.

## 🌟 System Architecture (6-Agent LangGraph)

The core brain of this copilot is built using **LangGraph**, utilizing a State Graph to route tasks among 6 specialized AI nodes:

1. **Intake Node**: Analyzes the initial user request, extracts the desired product, budget, and urgency, and maps it to a department.
2. **Search Node**: Searches the company's approved catalog (Database) or external sources for products matching the user's criteria.
3. **Vendor Node**: Evaluates and selects the best vendor/supplier for the requested product based on price, reliability, and delivery speed.
4. **Policy Node**: Checks the proposed purchase against the company's internal procurement policies (e.g., hardware budget limits, required approvals).
5. **Budget Node**: Verifies if the requesting department has sufficient budget remaining for this purchase.
6. **Human Review Node**: A final checkpoint that pauses the workflow, presenting a comprehensive summary of the AI's findings for a human manager to Approve or Reject.

All workflow states are persistently saved using **Postgres Checkpointer** via Supabase, allowing long-running tasks to be paused and resumed seamlessly.

## 🛠 Tech Stack

- **Backend (AI & API):** Python 3.12, FastAPI, LangGraph, LangChain, SQLAlchemy.
- **LLM Engine:** Groq API (Llama-3-70b/8b) for blazing-fast agentic reasoning.
- **Database & State Management:** Supabase (PostgreSQL) + pgvector.
- **Package Manager:** `uv` - an extremely fast Python package and project manager.
- **Frontend:** React, TypeScript, Vite, TailwindCSS (to be fully integrated).

## 🚀 Local Setup & Installation

### 1. Prerequisites
- Python 3.12+ and `uv` installed.
- Node.js 18+ and `npm`.
- A Supabase account and project.
- A Groq API Key.

### 2. Environment Variables
Create a `.env` file in both `backend/` and `frontend/` (if needed) using `.env.example` as a template.
For the backend (`backend/.env`):
```env
# Supabase Transaction Pooler (Port 6543)
DATABASE_URL="postgresql://postgres.[PROJECT_ID]:[PASSWORD]@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

# Groq LLM API Key
GROQ_API_KEY="your_groq_api_key"
```

### 3. Backend Setup
The backend uses `uv` for lightning-fast dependency management.
```bash
cd backend
uv sync
```

### 4. Frontend Setup
```bash
cd frontend
npm install
```

## 💻 Running the Application

**To run the AI Orchestrator Test Script (Terminal Mode):**
```bash
cd backend
uv run python scripts/test_orchestrator_v2.py
```

**To start the Backend API Server:**
```bash
cd backend
uv run uvicorn app.main:app --reload
```

**To start the Frontend Development Server:**
```bash
cd frontend
npm run dev
```

## 📝 License
MIT License
