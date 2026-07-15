from datetime import datetime, timedelta
from typing import List, Dict, Any
from langchain_core.tools import tool
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import SessionLocal
from app.models import PurchaseRequest, User

@tool
def check_recent_requests(department_id: str, category_keywords: str) -> str:
    """
    Check for recent purchase requests (within 7 days) across the company.
    Use this to detect Duplicate Requests or Demand Aggregation opportunities.
    Pass the user's department_id and keywords relating to the product category (e.g. 'laptop', 'monitor').
    """
    db: Session = SessionLocal()
    try:
        # Search requests in the last 7 days containing the keywords
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        # Simple ilike search on title or description for the keywords
        keyword = category_keywords.lower()
        recent_reqs = db.query(PurchaseRequest).filter(
            PurchaseRequest.created_at >= seven_days_ago,
            (PurchaseRequest.title.ilike(f"%{keyword}%") | PurchaseRequest.description.ilike(f"%{keyword}%"))
        ).all()
        
        if not recent_reqs:
            return "No recent requests found for this category. Safe to proceed."
            
        same_dept_reqs = []
        other_dept_reqs = []
        
        for req in recent_reqs:
            # Get requester's department
            requester = db.query(User).filter(User.id == req.requester_id).first()
            if not requester:
                continue
                
            req_info = f"ReqID: {req.id} | Amount: ${req.total_amount} | Status: {req.status} | Title: {req.title}"
            if str(requester.department_id) == department_id:
                same_dept_reqs.append(req_info)
            else:
                other_dept_reqs.append(f"Dept: {requester.department.name} | {req_info}")
                
        report = []
        if same_dept_reqs:
            report.append("WARNING (DUPLICATE): Recent requests found IN THE SAME DEPARTMENT:")
            report.extend(same_dept_reqs)
        if other_dept_reqs:
            report.append("INFO (DEMAND AGGREGATION): Recent requests found IN OTHER DEPARTMENTS:")
            report.extend(other_dept_reqs)
            
        return "\n".join(report)
    except Exception as e:
        return f"Error checking recent requests: {str(e)}"
    finally:
        db.close()

@tool
def check_cumulative_spend(requester_id: str, days: int = 30) -> str:
    """
    Check the cumulative spend of a user in the last N days (default 30).
    Use this to detect Budget Splitting (Smurfing) attempts where a user tries to bypass auto-approval limits.
    """
    db: Session = SessionLocal()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        total = db.query(func.sum(PurchaseRequest.total_amount)).filter(
            PurchaseRequest.requester_id == requester_id,
            PurchaseRequest.created_at >= start_date,
            PurchaseRequest.status != "rejected"
        ).scalar()
        
        total = total or 0.0
        return f"User {requester_id} has a cumulative spend of ${total:.2f} in the last {days} days."
    except Exception as e:
        return f"Error checking cumulative spend: {str(e)}"
    finally:
        db.close()
