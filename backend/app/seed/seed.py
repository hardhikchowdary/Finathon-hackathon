import random
import json
import os
from datetime import datetime, timedelta
from app.db import engine, SessionLocal, Base
from app.models import (
    Employee, Skill, SkillAlias, SkillRelation, Domain, Project,
    ProjectSkill, Assignment, Certification, EmployeeCertification,
    TrainingRecord, SelfDeclaredSkill, Course
)
from app.config import settings

def load_json(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), 'r') as f:
        return json.load(f)

def get_ref_date():
    if settings.REFERENCE_DATE:
        return datetime.fromisoformat(settings.REFERENCE_DATE)
    return datetime.now()

def main():
    random.seed(42)
    ref_date = get_ref_date()

    # Create tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Load and seed taxonomy
    tax_data = load_json('taxonomy.json')
    skill_map = {}
    
    for s_data in tax_data['skills']:
        skill = Skill(name=s_data['name'], category=s_data['category'])
        db.add(skill)
        db.flush()
        skill_map[s_data['name']] = skill.id
        for alias in s_data['aliases']:
            db.add(SkillAlias(skill_id=skill.id, alias=alias))
            
    for d_data in tax_data['domains']:
        db.add(Domain(name=d_data['name'], keywords=d_data['keywords']))
        
    for r_data in tax_data['relations']:
        if r_data['skill_a'] in skill_map and r_data['skill_b'] in skill_map:
            db.add(SkillRelation(
                skill_a_id=skill_map[r_data['skill_a']],
                skill_b_id=skill_map[r_data['skill_b']],
                strength=r_data['strength']
            ))
            
    # Load courses
    courses_data = load_json('courses.json')
    for c_data in courses_data:
        if c_data['skill'] in skill_map:
            db.add(Course(
                title=c_data['title'],
                provider=c_data['provider'],
                skill_id=skill_map[c_data['skill']],
                from_level=c_data['from_level'],
                to_level=c_data['to_level'],
                hours=c_data['hours'],
                points_gain=c_data['points_gain']
            ))
            
    db.commit()

    domains = db.query(Domain).all()
    fintech_domain = next(d for d in domains if d.name == "fintech")
    ecommerce_domain = next(d for d in domains if d.name == "e-commerce")
    
    react_id = skill_map.get("React")
    node_id = skill_map.get("Node.js")
    pci_id = skill_map.get("PCI-DSS")
    payments_id = skill_map.get("Payments Integration")
    java_id = skill_map.get("Java")

    # Generate 100 Employees
    departments = ["Frontend", "Backend", "Platform", "Data", "QA", "Security", "Product"]
    levels = ["Junior", "Mid", "Senior", "Lead"]
    
    employees = []
    
    # Planted scenarios
    planted = [
        {"id": 7, "name": "Ananya Rao", "role": "Senior Engineer", "dept": "Frontend", "level": "Senior"},
        {"id": 8, "name": "Rohan Iyer", "role": "Lead Engineer", "dept": "Backend", "level": "Lead"},
        {"id": 9, "name": "Meera Nair", "role": "Engineer", "dept": "Frontend", "level": "Mid"},
        {"id": 10, "name": "Karthik Reddy", "role": "Engineer", "dept": "Frontend", "level": "Mid"},
        {"id": 11, "name": "Sana Khan", "role": "Junior Engineer", "dept": "Frontend", "level": "Junior"},
        {"id": 12, "name": "Vikram Shah", "role": "Senior Engineer", "dept": "Frontend", "level": "Senior"},
        {"id": 13, "name": "Divya Menon", "role": "Lead Engineer", "dept": "Backend", "level": "Lead"},
        {"id": 14, "name": "Arjun Patel", "role": "Engineer", "dept": "Backend", "level": "Mid"},
    ]
    
    planted_ids = {p["id"] for p in planted}
    
    for p in planted:
        emp = Employee(id=p["id"], name=p["name"], email=f"{p['name'].lower().replace(' ', '.')}@example.com", role=p["role"], department=p["dept"], level=p["level"], location="Remote")
        db.add(emp)
        employees.append(emp)
        
    for i in range(1, 101):
        if i in planted_ids:
            continue
        emp = Employee(id=i, name=f"Employee {i}", email=f"emp{i}@example.com", role="Engineer", department=random.choice(departments), level=random.choice(levels), location="Office")
        db.add(emp)
        employees.append(emp)
        
    db.commit()

    # Generate Projects
    def make_project(pid, name, desc, domain, complexity, months_ago_start, months_duration, skills):
        start = ref_date - timedelta(days=30 * months_ago_start)
        end = start + timedelta(days=30 * months_duration) if months_duration else None
        end_str = end.isoformat()[:10] if end else None
        
        proj = Project(
            id=pid, name=name, description=desc, domain_id=domain.id if domain else None,
            complexity=complexity, start_date=start.isoformat()[:10], end_date=end_str,
            _truth_skills=skills
        )
        db.add(proj)
        
        # We also create project_skill manually to bypass extraction for seeding simplicity,
        # but the SRD says "extracted" for projects. We will simulate extraction.
        for s in skills:
            db.add(ProjectSkill(project_id=pid, skill_id=s, confidence=0.9, source="extracted"))
            
        return proj

    # Projects for Ananya (React 3 recent, Node 2, 2 fintech)
    p1 = make_project(1, "Fintech Dashboard", "Built the customer dashboard using ReactJS and a NodeJS/Express API for banking.", fintech_domain, 4, 12, 6, [react_id, node_id, payments_id])
    p2 = make_project(2, "Wallet App", "React Native and React web for digital wallet.", fintech_domain, 3, 6, 4, [react_id])
    p3 = make_project(3, "Internal Tool", "Internal CRM with React.", ecommerce_domain, 2, 2, None, [react_id, node_id]) # Ongoing

    # Projects for Rohan (Node 2, React 2, 1 fintech)
    p4 = make_project(4, "Payment Gateway API", "Node.js API for payment gateway.", fintech_domain, 5, 10, 8, [node_id, payments_id, pci_id])
    p5 = make_project(5, "E-commerce Backend", "Node and React for store.", ecommerce_domain, 4, 1, None, [node_id, react_id]) # Ongoing

    # Projects for Meera (React and Node, no fintech, no PCI)
    p6 = make_project(6, "Health Portal", "React frontend for telehealth.", None, 3, 8, 4, [react_id])
    p7 = make_project(7, "Logistics API", "Node.js backend for delivery tracking.", None, 3, 4, 2, [node_id])

    # Projects for Karthik (Strong React, Node weak)
    p8 = make_project(8, "Store UI", "React frontend.", ecommerce_domain, 3, 5, 3, [react_id])
    p9 = make_project(9, "Old Script", "A tiny node js script.", None, 1, 36, 1, [node_id])

    # Vikram (Heavy React 4+ years ago)
    p10 = make_project(10, "Legacy UI", "React webapp.", ecommerce_domain, 4, 50, 6, [react_id])
    
    # Divya (Node expert)
    p11 = make_project(11, "Core API", "Node.js core microservices.", fintech_domain, 5, 20, 10, [node_id])
    p12 = make_project(12, "Ledger API", "Node js ledger.", fintech_domain, 4, 8, None, [node_id])
    
    # Arjun (Java, Payments, PCI)
    p13 = make_project(13, "Bank Core", "Java Spring Boot for banking core with PCI compliance and payment integration.", fintech_domain, 5, 15, 10, [java_id, pci_id, payments_id])

    # Add remaining projects up to 40
    for pid in range(14, 41):
        make_project(pid, f"Project {pid}", f"Description {pid} using React and Node", random.choice(domains), 3, random.randint(5, 30), random.randint(2, 12), [react_id, node_id])

    db.commit()

    # Assignments
    def assign(emp_id, proj_id, role, pct, start_offset, end_offset=None):
        start = ref_date - timedelta(days=start_offset)
        end = start + timedelta(days=end_offset) if end_offset else None
        db.add(Assignment(employee_id=emp_id, project_id=proj_id, role=role, allocation_pct=pct,
                          start_date=start.isoformat()[:10], end_date=end.isoformat()[:10] if end else None))

    # Ananya utilization ~30%
    assign(7, 1, "Lead", 50, 360, 180)
    assign(7, 2, "Lead", 50, 180, 60)
    assign(7, 3, "Lead", 0.3, 60) # 30% utilization ongoing

    # Rohan utilization ~90%
    assign(8, 4, "Lead", 100, 300, 60)
    assign(8, 5, "Lead", 0.9, 30) # 90% ongoing

    # Meera
    assign(9, 6, "Contributor", 100, 240, 120)
    assign(9, 7, "Contributor", 100, 120, 60)
    
    # Karthik
    assign(10, 8, "Contributor", 100, 150, 60)
    assign(10, 9, "Contributor", 10, 1080, 1050)
    
    # Vikram
    assign(12, 10, "Lead", 100, 1500, 1320)
    
    # Divya ~60%
    assign(13, 11, "Lead", 100, 600, 300)
    assign(13, 12, "Architect", 0.6, 240) # 60% ongoing

    # Arjun
    assign(14, 13, "Contributor", 100, 450, 150)

    # Random assignments for others
    for i in range(15, 101):
        if i in planted_ids: continue
        assign(i, random.randint(14, 40), "Contributor", random.choice([0.5, 1.0]), random.randint(100, 500), random.randint(30, 90))
        
    db.commit()

    # Self Declared
    db.add(SelfDeclaredSkill(employee_id=11, skill_id=react_id))
    db.add(SelfDeclaredSkill(employee_id=11, skill_id=node_id))
    
    db.commit()
    print("Seeding complete.")

if __name__ == "__main__":
    main()
