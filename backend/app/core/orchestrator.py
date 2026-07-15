import operator
from typing import TypedDict, Annotated, Sequence, Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
from app.tools.budget_tools import check_budget, reserve_budget
from app.tools.search_products import search_products
from app.tools.vendor_comparison import compare_vendors
from app.core.graph_rag import query_policy_graph
from app.core.config import settings

# 1. Định nghĩa AgentState mở rộng cho 6 Agents
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    product_query: str
    department_name: str
    
    # 1. Intake
    parsed_category: str
    
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
    prompt = f"Trích xuất danh mục sản phẩm từ yêu cầu sau: '{query}'. Bạn CHỈ trả về đúng tên danh mục (vd: Electronics/Laptop, Software, Furniture), tuyệt đối không nói thêm câu nào."
    res = llm.invoke(prompt)
    category = res.content.strip()
    return {
        "parsed_category": category,
        "messages": [AIMessage(content=f"[Intake] Danh mục được xác định: {category}")]
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
    
    prompt = f"""Dựa vào kết quả tìm kiếm: '{search_summary}', hãy chọn ra MỘT sản phẩm tốt nhất.
    Yêu cầu ĐẦU RA BẮT BUỘC PHẢI THEO FORMAT SAU (chỉ ghi 2 dòng này, không giải thích):
    PRODUCT_NAME: <tên sản phẩm>
    COST: <giá bằng số>
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
                # keep only digits/dots
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
        "vendor_summary": f"Chọn {product_name} với giá {cost}",
        "messages": [AIMessage(content=f"[Vendor] Đề xuất chọn {product_name} với giá {cost}.")]
    }

def policy_node(state: AgentState):
    print("--- [NODE 4] Policy Checker ---")
    from app.core.graph_rag import query_policy_graph
    policy_info = query_policy_graph(state["product_query"])
    
    llm = get_llm()
    cost = state.get("total_cost", 0.0)
    prompt = f"""Dựa vào thông tin chính sách: '{policy_info}' và giá trị đơn hàng là ${cost}.
    Đơn hàng này có vi phạm chính sách hoặc cần sếp duyệt không?
    Trả về ĐÚNG 1 dòng format: 
    FLAG: <APPROVED hoặc NEEDS_APPROVAL hoặc REJECTED> - Lý do: <ngắn gọn>
    """
    res = llm.invoke(prompt)
    
    return {
        "policy_flags": res.content,
        "messages": [AIMessage(content=f"[Policy] {res.content}")]
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
