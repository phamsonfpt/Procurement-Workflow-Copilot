import json
import asyncio
import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from typing import Optional
from app.core.orchestrator import build_orchestrator
from app.core.checkpointer import get_checkpointer, get_pool
from app.core.retrieval_engine import retrieve_and_answer

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    department_name: Optional[str] = "Engineering"
    thread_id: Optional[str] = None # Hỗ trợ tiếp tục thread cũ
    user_role: Optional[str] = "Requester"
    email: Optional[str] = None

@router.post("")
async def chat_endpoint(request: ChatRequest):
    # Dùng thread_id do user truyền lên hoặc tạo mới
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    async def event_generator():
        try:
            # Lấy Postgres Checkpointer (tự động manage connection pool)
            async with get_checkpointer() as checkpointer:
                # Compile graph với checkpointer
                app = build_orchestrator(checkpointer)
                
                # Fetch state hiện tại xem luồng đã từng chạy chưa
                current_state = await app.aget_state(config)
                
                # Nếu chưa chạy (không có next step), khởi tạo state ban đầu
                if not current_state.next:
                    initial_state = {
                        "messages": [],
                        "department_name": request.department_name,
                        "product_query": request.query,
                        "requester_id": request.email
                    }
                    input_data = initial_state
                    
                    # Log to DB
                    pool = get_pool()
                    async with pool.connection() as conn:
                        await conn.execute(
                            "INSERT INTO procurement_requests (thread_id, requester_email, title, total_cost, status, required_role) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                            (thread_id, request.email, request.query[:50], 0, "PROCESSING", "None")
                        )
                else:
                    # Nếu đang ở trạng thái ngắt (chờ duyệt), thực hiện RBAC Security Check
                    required_role = current_state.values.get("required_approval_role", "None")
                    user_role = request.user_role
                    
                    role_hierarchy = {
                        "Requester": 0,
                        "Line Manager": 1,
                        "Department Head": 2,
                        "CFO": 3
                    }
                    
                    user_level = role_hierarchy.get(user_role, 0)
                    required_level = role_hierarchy.get(required_role, 0)
                    
                    if user_level < required_level:
                        yield f"data: {json.dumps({'type': 'error', 'content': f'Access Denied: Quyền hạn của bạn ({user_role}) không đủ để duyệt đơn hàng này. Yêu cầu cấp {required_role}.'})}\n\n"
                        return
                        
                    # Cho phép tiếp tục luồng
                    input_data = None
                
                yield f"data: {json.dumps({'type': 'thread_info', 'thread_id': thread_id})}\n\n"
                
                # Chạy luồng
                async for output in app.astream(input_data, config=config, stream_mode="updates"):
                    for node_name, state_changes in output.items():
                        
                        # Yield trạng thái (Node nào đang chạy)
                        yield f"data: {json.dumps({'type': 'status', 'node': node_name})}\n\n"
                        
                        # Trích xuất message nếu có để hiển thị lên Chat UI
                        if "messages" in state_changes and len(state_changes["messages"]) > 0:
                            last_msg = state_changes["messages"][-1].content
                            yield f"data: {json.dumps({'type': 'message', 'sender': node_name.capitalize(), 'content': last_msg})}\n\n"
                            
                    await asyncio.sleep(0.5)
                
                # Sau khi chạy xong, check xem có đang bị interrupt không
                final_state = await app.aget_state(config)
                
                # Cập nhật DB
                cost = final_state.values.get("total_cost", 0.0)
                req_role = final_state.values.get("required_approval_role", "None")
                prod_name = final_state.values.get("recommended_product_name", request.query[:50])
                
                pool = get_pool()
                
                if final_state.next:
                    # Bị ngắt (chờ duyệt)
                    async with pool.connection() as conn:
                        await conn.execute(
                            "UPDATE procurement_requests SET status = 'PENDING', total_cost = %s, required_role = %s, title = %s, updated_at = CURRENT_TIMESTAMP WHERE thread_id = %s",
                            (cost, req_role, prod_name, thread_id)
                        )
                    yield f"data: {json.dumps({'type': 'interrupt', 'pending_node': final_state.next[0]})}\n\n"
                else:
                    # Hoàn thành
                    async with pool.connection() as conn:
                        await conn.execute(
                            "UPDATE procurement_requests SET status = 'APPROVED', total_cost = %s, required_role = %s, title = %s, updated_at = CURRENT_TIMESTAMP WHERE thread_id = %s",
                            (cost, req_role, prod_name, thread_id)
                        )
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
        except Exception as e:
            # Update DB to FAILED so it doesn't get stuck in PROCESSING forever
            try:
                pool = get_pool()
                async with pool.connection() as conn:
                    await conn.execute(
                        "UPDATE procurement_requests SET status = 'FAILED', title = %s WHERE thread_id = %s",
                        ("System Error - Rate Limit or Crash", thread_id)
                    )
            except:
                pass
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# =====================================================================
# /ask endpoint — Direct Document Q&A (Multi-Tier Retrieval)
# =====================================================================
class AskRequest(BaseModel):
    query: str

@router.post("/ask")
async def ask_endpoint(request: AskRequest):
    """
    Direct document Q&A endpoint.
    Uses the multi-tier retrieval engine:
      - Intent Router classifies query
      - Simple QA → Hybrid Vector RAG (BM25 + pgvector)
      - Workflow Reasoning → LightRAG (Knowledge Graph)
      - LLM generates answer from retrieved context
    """
    try:
        result = await retrieve_and_answer(request.query)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )

# =====================================================================
# /reject endpoint — Ops Rejection
# =====================================================================
class RejectRequest(BaseModel):
    thread_id: str
    email: str
    user_role: str

@router.post("/reject")
async def reject_endpoint(request: RejectRequest):
    role_hierarchy = {
        "Requester": 0,
        "Line Manager": 1,
        "Department Head": 2,
        "CFO": 3,
        "Ops": 4
    }
    
    if role_hierarchy.get(request.user_role, 0) < 1:
        return JSONResponse(status_code=403, content={"error": "Access Denied: You do not have permission to reject."})
        
    try:
        pool = get_pool()
        async with pool.connection() as conn:
            await conn.execute(
                "UPDATE procurement_requests SET status = 'REJECTED', updated_at = CURRENT_TIMESTAMP WHERE thread_id = %s",
                (request.thread_id,)
            )
        return {"status": "success", "message": f"Request {request.thread_id} rejected."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

