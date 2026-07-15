import operator
from typing import TypedDict, Annotated, Sequence, Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
from app.tools.budget_tools import check_budget, reserve_budget
from app.tools.search_products import search_products
from app.tools.vendor_comparison import compare_vendors
from app.tools.history_tools import check_recent_requests, check_cumulative_spend
from app.core.graph_rag import query_policy_graph
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
    prod_id = res_ext.content.strip()
    
    vendor_comparison = "No comparison available."
    if len(prod_id) >= 32: # basic UUID check
        vendor_comparison = compare_vendors.invoke({"product_id": prod_id, "quantity": qty})
    
    prompt = f"""Dựa vào kết quả so sánh Vendor: '{vendor_comparison}', hãy chọn ra deal tốt nhất cho số lượng {qty}.
    Yêu cầu ĐẦU RA BẮT BUỘC PHẢI THEO FORMAT SAU (chỉ ghi 2 dòng này, không giải thích):
    PRODUCT_NAME: <tên sản phẩm và vendor được chọn>
    COST: <tổng chi phí Total Cost bằng số>
    """
    res = llm.invoke(prompt)
    content = res.content
    
    # Parse
    product_name = "Unknown"
    cost = 0.0
    for line in content.split('\n'):
        if line.startswith("PRODUCT_NAME:"):
            product_name = line.replace("PRODUCT_NAME:", "").strip()
        elif line.startswith("COST:"):
            try:
                num_str = ''.join(c for c in line if c.isdigit() or c == '.')
                cost = float(num_str) if num_str else 0.0
            except:
                pass
                
    if cost == 0.0:
        cost = 2500.0 # fallback
        product_name = "Default Product"
        
    return {
        "recommended_product_name": product_name,
        "total_cost": cost,
        "vendor_summary": f"Chọn {product_name} với tổng giá ${cost} (đã bao gồm chiết khấu sỉ nếu có).\n{vendor_comparison}",
        "messages": [AIMessage(content=f"[Vendor] Đề xuất chọn {product_name} với tổng chi phí ${cost}.\nChi tiết: {vendor_comparison}")]
    }

def policy_node(state: AgentState):
    print("--- [NODE 4] Policy Checker ---")
    from app.core.graph_rag import query_policy_graph
    
    # 1. Get explicit policies (Includes Maverick Spend and Role-based rules)
    policy_info = query_policy_graph(state["product_query"] + " " + state["parsed_category"])
    
    # 2. Check cumulative spend (Smurfing detection)
    req_id = state.get("requester_id", "")
    spend_history = "Unknown spend history."
    if req_id:
        spend_history = check_cumulative_spend.invoke({"requester_id": req_id, "days": 30})
        
    llm = get_llm()
    cost = state.get("total_cost", 0.0)
    dept_name = state.get("department_name", "Unknown")
    
    prompt = f"""Dựa vào thông tin chính sách: '{policy_info}' 
    Và lịch sử chi tiêu của nhân viên này: '{spend_history}'
    Phòng ban của nhân viên: '{dept_name}'
    Giá trị đơn hàng hiện tại là: ${cost}.
    
    Đơn hàng này có vi phạm chính sách (như Role-based, Maverick Spend) hoặc có dấu hiệu Smurfing (lách luật chia nhỏ hóa đơn để vượt Auto-approve $500) không?
    Trả về ĐÚNG 1 dòng format: 
    FLAG: <APPROVED hoặc NEEDS_APPROVAL hoặc REJECTED> - Lý do: <ngắn gọn>
    """
    res = llm.invoke(prompt)
    
    return {
        "policy_flags": res.content,
        "messages": [AIMessage(content=f"[Policy]\nSpend History: {spend_history}\nDecision: {res.content}")]
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
        
        return {
            "budget_status": status,
            "error_msg": "" if status == "SUCCESS" else reserve_info,
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
    # Đây là node trống để LangGraph dừng lại chờ người dùng approve
    return {
        "approval_status": "PENDING_MANAGER_REVIEW",
        "messages": [AIMessage(content="[Review] Luồng tạm dừng chờ cấp quản lý duyệt.")]
    }

# ================= ROUTER =================

def route_after_budget(state: AgentState) -> str:
    print(f"--- [ROUTER] Checking Budget Status: {state.get('budget_status')} ---")
    if state.get("budget_status") == "FAILED":
        return "end" # Nếu thất bại, kết thúc luồng luôn (hoặc có thể lùi về Intake)
    return "human_review" # Nếu OK, sang Node 6 chờ duyệt

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
