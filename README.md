# Procurement Workflow Copilot 🚀

A full-stack, enterprise-grade AI Procurement system built with **LangGraph**, **FastAPI**, **React**, and **PostgreSQL**. This project demonstrates how to orchestrate autonomous AI agents to handle corporate purchasing workflows, complete with dynamic policy enforcement, budget reservation, and Role-Based Access Control (RBAC).

---

## 🌟 Key Enterprise Features

1. **AI Agentic Workflow (LangGraph)**
   - The system is not a simple chatbot. It is a multi-agent orchestration pipeline where different AI nodes handle distinct business logics: `Intake -> Search -> Vendor Analysis -> Policy Check -> Budget Reservation -> Human Review`.
   
2. **Dynamic Approval Matrix & RBAC Security**
   - The AI dynamically determines the required approval authority based on the purchase cost (e.g., `< $1000` goes to Line Manager, `>= $5000` requires CFO).
   - **Backend Enforced**: Approvals are validated securely on the backend. Attempting to approve a high-value request with insufficient privileges throws an `Access Denied` error.

3. **Anti-Fraud & Smurfing Detection**
   - The AI `Policy Checker` connects to the database to track cumulative employee spend over 30 days.
   - If an employee attempts to bypass auto-approval limits by splitting large purchases into multiple small ones (Smurfing), the AI automatically flags the request and escalates the approval role to a Department Head.

4. **Multi-Page Enterprise Dashboard (React Router)**
   - Different users get completely different views:
     - **Requester**: Simple chat interface to submit orders.
     - **Manager / CFO**: Dashboard showing a queue of pending requests needing their approval.
     - **Procurement Ops**: Global view of all corporate spend with the power to "Force Override" approvals.
     - **IT Admin**: System monitor displaying server health, API quotas, and LangGraph trace logs.

5. **State Persistence & Fault Tolerance**
   - Powered by **Postgres Checkpointer**. Every step of the AI's thought process and every chat message is saved to PostgreSQL. If the server crashes mid-thought, the exact state is recovered immediately.

---

## 🛠 Tech Stack

- **Backend Architecture**: Python 3.12, FastAPI, LangGraph, LangChain.
- **LLM Engine**: Groq (LLaMA 3.3 70B) for ultra-fast, ultra-cheap agentic reasoning.
- **Frontend Architecture**: React 19, TypeScript, Vite, React Router, Tailwind-inspired Vanilla CSS.
- **Database**: Supabase (PostgreSQL), `psycopg-pool`.

---

## 🎮 How to Demo the System

The application comes with 6 pre-configured Active Directory (SSO) roles. Run the app and login with these emails to test different scenarios:

### Scenario 1: Auto-Approval ($100 Keyboard)
1. Login with `employee@acme.corp` (Requester).
2. Type: *"I need to buy a $100 mechanical keyboard."*
3. The AI will search, check policies, reserve budget, and auto-approve without human intervention.

### Scenario 2: RBAC Matrix ($6000 Server)
1. Login with `employee@acme.corp` (Requester).
2. Type: *"Order a high-end AI Server for $6000."*
3. The AI pauses the workflow and demands CFO approval.
4. Try to type *"Approve"*. The backend will block you.
5. Sign out. Login with `manager@acme.corp` (Line Manager). Try to approve. Blocked again!
6. Sign out. Login with `cfo@acme.corp` (CFO). Open the pending thread and approve it successfully.

### Scenario 3: Global Operations Override
1. Login with `ops@acme.corp` (Procurement Ops).
2. You will see a global dashboard of ALL requests across the company.
3. If a request is stuck pending for too long, click **Force Override** to bypass the approval chain.

### Scenario 4: System Monitoring
1. Login with `admin@acme.corp` (IT Admin).
2. View the mock System Logs, API quotas, and Database Connection Pool health.

---

## 🚀 Running Locally

1. **Backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. **Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

*Note: You must have a `GROQ_API_KEY` and `DATABASE_URL` (Supabase) in your backend `.env` file.*
