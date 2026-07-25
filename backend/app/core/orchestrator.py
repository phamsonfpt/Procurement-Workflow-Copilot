import operator
from typing import TypedDict, Annotated, Sequence, Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
from app.tools.budget_tools import check_budget, reserve_budget
from app.tools.search_products import search_products
from app.tools.vendor_comparison import compare_vendors
from app.tools.history_tools import check_recent_requests, check_cumulative_spend
from app.core.retrieval_engine import retrieve_context_only_sync
from app.core.config import settings

# 1. Định nghĩa AgentState mở rộng cho 6 Agents
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    product_query: str
    department_name: str
    department_id: str
    requester_id: str
    quantity: int
    
    # 1. Intake
    parsed_category: str
    duplicate_or_aggregate_flag: str
    
    # 2. Search
    search_summary: str
    
    # 3. Vendor
    recommended_product_name: str
    vendor_summary: str
    total_cost: float
    
    # 4. Policy
    policy_flags: str
    
    # 5. Budget
    budget_status: str
    error_msg: str
    
    # 6. Human Review
    approval_status: str
    required_approval_role: str

def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile", 
        temperature=0, 
        api_key=settings.GROQ_API_KEY,
        timeout=30.0 # Bọc Timeout 30s
    )

def _mock_llm_call(node_name: str, fallback_state: dict):
    # Hàm helper trả về mock data do API Key bị quota
    print(f"[{node_name}] LLM Quota Exceeded. Using Fallback Mock Data.")
    return fallback_state

# ================= NODES =================

def intake_node(state: AgentState):
    print("--- [NODE 1] Intake ---")
    llm = get_llm()
    query = state.get("product_query", "")
    dept_id = state.get("department_id", "")
    
    # Extract category and quantity
    prompt = f"""Trích xuất danh mục sản phẩm và số lượng từ yêu cầu sau: '{query}'. 
    Trả về ĐÚNG 2 dòng format:
    CATEGORY: <tên danh mục (vd: Laptop, Monitor)>
    QTY: <số lượng (integer)>
    """
    res = llm.invoke(prompt)
    
    category = "Unknown"
    qty = 1
    for line in res.content.split('\n'):
        if line.startswith("CATEGORY:"):
            category = line.replace("CATEGORY:", "").strip()
        elif line.startswith("QTY:"):
            try:
                qty = int(line.replace("QTY:", "").strip())
            except:
                qty = 1
                
    # Check history for Duplicate or Aggregation
    history_report = "No history checked."
    if dept_id:
        history_report = check_recent_requests.invoke({"department_id": dept_id, "category_keywords": category})
        
    return {
        "parsed_category": category,
        "quantity": qty,
        "duplicate_or_aggregate_flag": history_report,
        "messages": [AIMessage(content=f"[Intake] Danh mục: {category}, Số lượng: {qty}\n[History Check]: {history_report}")]
    }

def search_node(state: AgentState):
    print("--- [NODE 2] Search ---")
    llm = get_llm()
    query = state.get("parsed_category", "") or state.get("product_query", "")
    
    # Run tool
    from app.tools.search_products import search_products
    search_results = search_products.invoke({"query": query})
    
    # Summarize with LLM
    prompt = f"Tôi có danh sách sản phẩm sau: {search_results}. Hãy tóm tắt ngắn gọn thành 1 câu."
    res = llm.invoke(prompt)
    
    return {
        "search_summary": res.content,
        "messages": [AIMessage(content=f"[Search] {res.content}")]
    }

def vendor_node(state: AgentState):
    print("--- [NODE 3] Vendor Analyst ---")
    llm = get_llm()
    search_summary = state.get("search_summary", "")
    qty = state.get("quantity", 1)
    
    # Get first product ID from search summary (Naive extraction for demo, in reality we'd parse search_results)
    # Let's use compare_vendors directly on the best match. 
    # But wait, search_products returns strings. Let's let the LLM extract the product ID.
    prompt_extract = f"Từ '{search_summary}', hãy tìm ID của sản phẩm đầu tiên. Trả về đúng UUID, không nói gì thêm."
    res_ext = llm.invoke(prompt_extract)
    
    import re
    uuid_match = re.search(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', res_ext.content)
    prod_id = uuid_match.group(0) if uuid_match else ""
    
    vendor_comparison = "No comparison available."
    if prod_id:
        vendor_comparison = compare_vendors.invoke({"product_id": prod_id, "quantity": qty})
    
    prompt = f"""Dựa vào kết quả so sánh Vendor: '{vendor_comparison}', hãy chọn ra deal tốt nhất cho số lượng {qty}.
    Yêu cầu ĐẦU RA BẮT BUỘC PHẢI THEO FORMAT SAU (chỉ ghi 2 dòng này, không giải thích):
    PRODUCT_NAME: <tên sản phẩm và vendor được chọn>
    UNIT_PRICE: <đơn giá (chỉ ghi số)>
    """
    res = llm.invoke(prompt)
    content = res.content
    
    # Parse
    product_name = "Unknown"
    unit_cost = 0.0
    for line in content.split('\n'):
        if line.startswith("PRODUCT_NAME:"):
            product_name = line.replace("PRODUCT_NAME:", "").strip()
        elif line.startswith("UNIT_PRICE:"):
            try:
                num_str = ''.join(c for c in line if c.isdigit() or c == '.')
                unit_cost = float(num_str) if num_str else 0.0
            except:
                pass
                
    if unit_cost == 0.0:
        # fallback to extracting cost from query if vendor parsing fails
        import re
        cost_match = re.search(r'\$(\d+(?:\.\d+)?)', state.get("product_query", ""))
        unit_cost = float(cost_match.group(1)) if cost_match else 250.0
        product_name = state.get("parsed_category", "Unknown Product")
        
    cost = unit_cost * qty

        
    return {
        "recommended_product_name": product_name,
        "total_cost": cost,
        "vendor_summary": f"Chọn {product_name} với tổng giá ${cost} (đã bao gồm chiết khấu sỉ nếu có).\n{vendor_comparison}",
        "messages": [AIMessage(content=f"[Vendor] Đề xuất chọn {product_name} với tổng chi phí ${cost}.\nChi tiết: {vendor_comparison}")]
    }

async def policy_node(state: AgentState):
    print("--- [NODE 4] Policy Checker ---")
    # 1. Get explicit policies via multi-tier retrieval (auto-routes to Vector RAG or LightRAG)
    policy_info = retrieve_context_only_sync(state["product_query"] + " " + state["parsed_category"])
    
    # 2. Check cumulative spend (Smurfing detection) directly via DB
    req_email = state.get("requester_id", "")
    spend_history = "Unknown spend history."
    if req_email:
        from app.core.checkpointer import get_pool
        pool = get_pool()
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT SUM(total_cost) FROM procurement_requests WHERE requester_email = %s AND status IN ('APPROVED', 'PENDING') AND updated_at > NOW() - INTERVAL '30 days'",
                        (req_email,)
                    )
                    row = await cur.fetchone()
                    total = float(row[0]) if row and row[0] else 0.0
                    spend_history = f"User {req_email} has a cumulative spend of ${total:.2f} in the last 30 days."
        except Exception as e:
            spend_history = f"Error checking history: {e}"
            total = 0.0
            
    llm = get_llm()
    cost = state.get("total_cost", 0.0)
    dept_name = state.get("department_name", "Unknown")
    
    # [Hardcode Python Logic] Explicit Smurfing Check
    is_smurfing = (total + cost >= 1000) and (cost < 1000)
    smurfing_directive = ""
    if is_smurfing:
        smurfing_directive = "CẢNH BÁO TỪ HỆ THỐNG: Python đã phát hiện Smurfing. BẠN BẮT BUỘC PHẢI TRẢ VỀ: FLAG: NEEDS_APPROVAL - Lý do: Phát hiện dấu hiệu chia nhỏ hóa đơn (Smurfing)."
    
    prompt = f"""Dựa vào thông tin chính sách: '{policy_info}' 
    Và lịch sử chi tiêu của nhân viên này: '{spend_history}'
    Phòng ban của nhân viên: '{dept_name}'
    Giá trị đơn hàng hiện tại là: ${cost}.
    
    LƯU Ý LUẬT CỨNG:
    - Mọi đơn hàng < $1000 đều được TỰ ĐỘNG PHÊ DUYỆT (APPROVED), TRỪ KHI phát hiện vi phạm Maverick Spend hoặc Smurfing.
    - Maverick Spend: Công ty CHỈ CHO PHÉP mua đồ Dell cho IT/Laptop tiêu chuẩn. CẤM mua Apple/MacBook (trừ khi dùng cho iOS dev ở Engineering). Mua hãng khác Dell là Maverick Spend.
    
    {smurfing_directive}
    
    Đơn hàng này có vi phạm chính sách (như Maverick Spend) hoặc có dấu hiệu Smurfing không?
    Trả về ĐÚNG 1 dòng format: 
    FLAG: <APPROVED hoặc NEEDS_APPROVAL hoặc REJECTED> - Lý do: <ngắn gọn>
    """
    res = await llm.ainvoke(prompt)
    
    # Đảm bảo Python đè quyết định nếu LLM vẫn ngoan cố
    final_decision = res.content
    if is_smurfing and "APPROVED" in final_decision:
        final_decision = "FLAG: NEEDS_APPROVAL - Lý do: [System Override] Phát hiện dấu hiệu chia nhỏ hóa đơn (Smurfing)."
    
    return {
        "policy_flags": final_decision,
        "messages": [AIMessage(content=f"[Policy]\nSpend History: {spend_history}\nDecision: {final_decision}")]
    }

def budget_node(state: AgentState):
    print("--- [NODE 5] Budget Reviewer ---")
    dept = state.get("department_name", "Engineering")
    cost = state.get("total_cost", 0.0)
    
    try:
        # Gọi tool trực tiếp (không qua LLM để đảm bảo an toàn & lock budget)
        budget_info = check_budget.invoke({"department_name": dept})
        reserve_info = reserve_budget.invoke({"department_name": dept, "amount": cost})
        
        status = "SUCCESS" if "Successfully" in reserve_info else "FAILED"
        msg = f"[Budget] Reserve result: {reserve_info}"
        
        # Escalate if Policy Checker detected an anomaly (e.g. Smurfing)
        policy_flags = state.get("policy_flags", "")
        force_escalation = "NEEDS_APPROVAL" in policy_flags or "REJECTED" in policy_flags

        # Determine Required Approval Role based on Matrix
        req_role = "None"
        if cost > 50000:
            req_role = "CFO"
        elif cost >= 10000:
            req_role = "Department Head"
        elif cost >= 1000:
            req_role = "Line Manager"
        
        # Ngăn chặn Smurfing: Dù giá trị thấp nhưng có dấu hiệu chia nhỏ hóa đơn
        if req_role == "None" and force_escalation:
            req_role = "Department Head" # Bắt buộc Trưởng phòng duyệt nếu nghi ngờ lách luật
            msg += "\n[Security] Cảnh báo: Phát hiện dấu hiệu chia nhỏ hóa đơn (Smurfing)! Buộc chuyển lên Trưởng phòng phê duyệt."
            
        return {
            "budget_status": status,
            "error_msg": "" if status == "SUCCESS" else reserve_info,
            "required_approval_role": req_role,
            "messages": [AIMessage(content=msg)]
        }
    except Exception as e:
        return {
            "budget_status": "FAILED",
            "error_msg": str(e),
            "messages": [AIMessage(content=f"[Budget] ERROR: {str(e)}")]
        }

def human_review_node(state: AgentState):
    print("--- [NODE 6] Human Review (Interrupt Point) ---")
    required_role = state.get("required_approval_role", "Manager")
    # Đây là node trống để LangGraph dừng lại chờ người dùng approve
    return {
        "approval_status": f"PENDING_{required_role.upper()}_REVIEW",
        "messages": [AIMessage(content=f"[Review] Đơn hàng cần được phê duyệt bởi cấp: {required_role}.")]
    }

# ================= ROUTER =================

def route_after_budget(state: AgentState) -> str:
    print(f"--- [ROUTER] Checking Budget Status: {state.get('budget_status')} ---")
    if state.get("budget_status") == "FAILED":
        return "end" # Nếu thất bại, kết thúc luồng luôn (hoặc có thể lùi về Intake)
        
    req_role = state.get("required_approval_role", "None")
    if req_role == "None":
        return "end" # Auto approve nếu không cần duyệt
        
    return "human_review" # Nếu cần duyệt, sang Node 6 chờ duyệt

# ================= GRAPH BUILDER =================

def build_orchestrator(checkpointer=None):
    workflow = StateGraph(AgentState)
    
    # Đăng ký 6 Nodes
    workflow.add_node("intake", intake_node)
    workflow.add_node("search", search_node)
    workflow.add_node("vendor", vendor_node)
    workflow.add_node("policy", policy_node)
    workflow.add_node("budget", budget_node)
    workflow.add_node("human_review", human_review_node)
    
    # Định tuyến (Forward)
    workflow.set_entry_point("intake")
    workflow.add_edge("intake", "search")
    workflow.add_edge("search", "vendor")
    workflow.add_edge("vendor", "policy")
    workflow.add_edge("policy", "budget")
    
    # Định tuyến điều kiện (Conditional)
    workflow.add_conditional_edges(
        "budget",
        route_after_budget,
        {
            "human_review": "human_review",
            "end": END
        }
    )
    
    workflow.add_edge("human_review", END)
    
    # Cài đặt Checkpointer (PostgresSaver) và Interrupts
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"] # Dừng trước khi vào Node 6
    )
