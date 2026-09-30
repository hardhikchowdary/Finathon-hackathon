from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import date

class SkillBase(BaseModel):
    id: int
    name: str
    category: str
    aliases: List[str] = []

    model_config = ConfigDict(from_attributes=True)

class EmployeeBase(BaseModel):
    id: int
    name: str
    role: str
    department: str
    level: str
    utilization: float

    model_config = ConfigDict(from_attributes=True)

class EmployeeListResponse(BaseModel):
    employees: List[EmployeeBase]

class HealthResponse(BaseModel):
    status: str
