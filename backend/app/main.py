from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
import sys
import asyncio
from contextlib import asynccontextmanager
from app.core.checkpointer import get_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize procurement_requests table
    pool = get_pool()
    async with pool.connection() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS procurement_requests (
                thread_id VARCHAR(255) PRIMARY KEY,
                requester_email VARCHAR(255),
                title TEXT,
                total_cost DECIMAL(10,2),
                status VARCHAR(50),
                required_role VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    yield

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Procurement Workflow Copilot",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For Vercel/Dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}

@app.get("/api/seed")
async def seed_database():
    import uuid
    import random
    from datetime import datetime, timedelta
    pool = get_pool()
    ITEMS = [
        ("Dell Latitude 5520", 1200.00, "Line Manager"),
        ("MacBook Pro M3", 2500.00, "Department Head"),
        ("Office Chair", 250.00, "None"),
        ("AWS Server Migration", 8500.00, "Department Head"),
        ("Enterprise ERP License", 55000.00, "CFO"),
        ("Marketing Campaign Tools", 450.00, "None"),
        ("Adobe Creative Cloud", 900.00, "Line Manager"),
        ("Company Event Catering", 3000.00, "Department Head"),
        ("AI Infrastructure Upgrade", 120000.00, "CFO"),
        ("Standing Desk", 450.00, "None"),
        ("Team Building Trip", 4800.00, "Department Head"),
        ("New Hire Welcome Kit", 150.00, "None"),
    ]
    REQUESTERS = [
        'emp1@acme.corp', 'emp2@acme.corp', 'emp3@acme.corp',
        'emp4@acme.corp', 'emp5@acme.corp', 'emp6@acme.corp',
        'emp7@acme.corp', 'emp8@acme.corp', 'emp9@acme.corp',
        'emp10@acme.corp'
    ]
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            for _ in range(40):
                thread_id = str(uuid.uuid4())
                requester = random.choice(REQUESTERS)
                item, cost, req_role = random.choice(ITEMS)
                status = "APPROVED" if req_role == "None" else random.choice(["PENDING", "PENDING", "APPROVED", "REJECTED"])
                days_ago = random.randint(0, 7)
                hours_ago = random.randint(0, 23)
                minutes_ago = random.randint(0, 59)
                created_at = datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
                updated_at = created_at + timedelta(minutes=random.randint(1, 120))
                await cur.execute("""
                    INSERT INTO procurement_requests 
                    (thread_id, requester_email, title, total_cost, status, required_role, created_at, updated_at) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (thread_id, requester, f"Request to buy {item}", cost, status, req_role, created_at, updated_at))
    return {"message": "Database seeded with 40 requests"}

from app.api.chat import router as chat_router
from app.api.requests import router as requests_router

app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(requests_router, prefix="/api/requests", tags=["Requests"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
