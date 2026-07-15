import json
import asyncio
import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.core.orchestrator import build_orchestrator
from app.core.checkpointer import get_checkpointer

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    department_name: Optional[str] = "Engineering"
    thread_id: Optional[str] = None # Hỗ trợ tiếp tục thread cũ

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
                        "product_query": request.query
                    }
                    input_data = initial_state
                else:
                    # Nếu đang ở trạng thái ngắt (ví dụ chờ duyệt human_review)
                    # Ta có thể resume nó bằng cách truyền input rỗng hoặc lệnh duyệt
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
                if final_state.next:
                    yield f"data: {json.dumps({'type': 'interrupt', 'pending_node': final_state.next[0]})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
