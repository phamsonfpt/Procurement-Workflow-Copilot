from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from app.core.checkpointer import get_pool
from datetime import datetime

router = APIRouter()

class RequestModel(BaseModel):
    thread_id: str
    requester_email: str
    title: str
    total_cost: float
    status: str
    required_role: str
    created_at: datetime
    updated_at: datetime

@router.get("", response_model=List[RequestModel])
async def get_requests(
    role: str = Query(...), 
    email: str = Query(...)
):
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            if role == "Requester":
                await cur.execute("SELECT * FROM procurement_requests WHERE requester_email = %s ORDER BY updated_at DESC", (email,))
            elif role in ["Line Manager", "Department Head", "CFO"]:
                await cur.execute("SELECT * FROM procurement_requests WHERE required_role = %s AND status = 'PENDING' ORDER BY updated_at DESC", (role,))
            elif role in ["Ops", "IT Admin"]:
                await cur.execute("SELECT * FROM procurement_requests ORDER BY updated_at DESC")
            else:
                return []
                
            rows = await cur.fetchall()
            
            requests = []
            for row in rows:
                requests.append(RequestModel(
                    thread_id=row[0],
                    requester_email=row[1],
                    title=row[2],
                    total_cost=float(row[3]),
                    status=row[4],
                    required_role=row[5],
                    created_at=row[6],
                    updated_at=row[7]
                ))
            return requests

class OverrideRequest(BaseModel):
    new_status: str
    admin_email: str

@router.post("/{thread_id}/override")
async def override_request(thread_id: str, payload: OverrideRequest):
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE procurement_requests SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE thread_id = %s",
                (payload.new_status, thread_id)
            )
    return {"message": "Override successful"}
