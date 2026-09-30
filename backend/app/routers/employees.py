from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from ..db import get_db
from ..models import Employee
from ..schemas import EmployeeBase

router = APIRouter(prefix="/api/employees", tags=["employees"])

@router.get("", response_model=List[EmployeeBase])
def get_employees(q: Optional[str] = None, department: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(Employee)
    if q:
        query = query.filter(Employee.name.ilike(f"%{q}%"))
    if department:
        query = query.filter(Employee.department == department)
        
    employees = query.limit(limit).all()
    
    # Calculate utilization manually for Phase 1 as per assignment
    # In a full implementation, utilization would be calculated based on active assignments
    # For now, we mock utilization or load it if we calculate it during seeding.
    # The assignment pct was stored as allocation_pct on assignments.
    
    # We will compute utilization properly by querying active assignments
    from ..models import Assignment
    from datetime import datetime
    
    ref_date_str = datetime.now().isoformat()[:10] # Simplified for phase 1
    
    results = []
    for emp in employees:
        active_assignments = db.query(Assignment).filter(
            Assignment.employee_id == emp.id,
            Assignment.start_date <= ref_date_str,
            (Assignment.end_date == None) | (Assignment.end_date >= ref_date_str)
        ).all()
        
        utilization = sum(a.allocation_pct for a in active_assignments)
        
        # Add utilization dynamically
        emp_dict = {
            "id": emp.id,
            "name": emp.name,
            "role": emp.role,
            "department": emp.department,
            "level": emp.level,
            "utilization": min(utilization, 1.0)
        }
        results.append(emp_dict)
        
    return results
