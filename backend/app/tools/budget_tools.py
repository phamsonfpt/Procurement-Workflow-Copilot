from langchain_core.tools import tool
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from decimal import Decimal
from app.database import SessionLocal
from app.models import Budget, Department

@tool
def check_budget(department_name: str) -> str:
    """
    Check the available budget for a specific department.
    Use this tool before reserving budget to ensure the department has enough funds.
    """
    db: Session = SessionLocal()
    try:
        dept = db.query(Department).filter(Department.name.ilike(f"%{department_name}%")).first()
        if not dept:
            return f"Department '{department_name}' not found."
            
        budget = db.query(Budget).filter(Budget.department_id == dept.id).first()
        if not budget:
            return f"No budget found for department '{dept.name}'."
            
        remaining = budget.total_budget - budget.used_budget
        return f"Department '{dept.name}' has a total budget of ${budget.total_budget}. Remaining available budget: ${remaining} (Version: {budget.version})"
    finally:
        db.close()

@tool
def reserve_budget(department_name: str, amount: float) -> str:
    """
    Reserve budget for a purchase. This uses Optimistic Locking to prevent race conditions.
    Use this tool to lock funds after a user has confirmed a purchase.
    """
    db: Session = SessionLocal()
    try:
        dept = db.query(Department).filter(Department.name.ilike(f"%{department_name}%")).first()
        if not dept:
            return f"Error: Department '{department_name}' not found."
            
        budget = db.query(Budget).filter(Budget.department_id == dept.id).first()
        if not budget:
            return f"Error: No budget found for department '{dept.name}'."
            
        amount_dec = Decimal(str(amount))
        
        remaining = budget.total_budget - budget.used_budget
        if remaining < amount_dec:
            return f"Error: Insufficient funds. Requested ${amount}, but only ${remaining} is available."
            
        # Attempt to reserve by updating the amount
        # Optimistic locking is handled automatically by SQLAlchemy because we set version_id_col in models.py
        budget.used_budget += amount_dec
        
        try:
            db.commit()
            new_remaining = budget.total_budget - budget.used_budget
            return f"Successfully reserved ${amount} for {dept.name}. New remaining budget: ${new_remaining} (Version: {budget.version})"
        except StaleDataError:
            db.rollback()
            return "Error (Optimistic Lock Failure): The budget was modified by another transaction while we were trying to update it. Please check the budget again and retry."
        except Exception as e:
            db.rollback()
            return f"Error reserving budget: {str(e)}"
            
    finally:
        db.close()
