import random
import uuid
import math
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from faker import Faker

# Adjust import paths depending on where this script is run from
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal, engine
from app.models import Base, Department, User, Budget, Product, Vendor, VendorProduct

fake = Faker()

def seed_departments(db: Session):
    print("Seeding departments...")
    depts = [
        {"name": "Engineering", "code": "ENG"},
        {"name": "Marketing", "code": "MKT"},
        {"name": "Sales", "code": "SALES"},
        {"name": "Human Resources", "code": "HR"},
        {"name": "Operations", "code": "OPS"}
    ]
    created_depts = []
    for d in depts:
        dept = Department(name=d["name"], code=d["code"])
        db.add(dept)
        created_depts.append(dept)
    db.commit()
    return created_depts

def seed_budgets(db: Session, departments: list):
    print("Seeding budgets...")
    budgets = [
        {"total": 500000.0, "used": 0.0},
        {"total": 200000.0, "used": 0.0},
        {"total": 150000.0, "used": 0.0},
        {"total": 50000.0, "used": 0.0},
        {"total": 300000.0, "used": 0.0},
    ]
    for i, dept in enumerate(departments):
        budget = Budget(
            department_id=dept.id,
            total_budget=budgets[i]["total"],
            used_budget=budgets[i]["used"],
            fiscal_year=2026,
            version=1
        )
        db.add(budget)
    db.commit()

def seed_users(db: Session, departments: list):
    print("Seeding users...")
    roles = ["employee", "manager", "cfo"]
    for dept in departments:
        # 1 manager, 3 employees per dept
        for i in range(4):
            role = "manager" if i == 0 else "employee"
            user = User(
                email=f"{fake.user_name()}@{dept.code.lower()}.company.com",
                name=fake.name(),
                role=role,
                department_id=dept.id,
                hashed_password="mock_hashed_password"
            )
            db.add(user)
    
    # 1 CFO
    cfo = User(
        email="cfo@company.com",
        name="Chief Financial Officer",
        role="cfo",
        department_id=None,
        hashed_password="mock_hashed_password"
    )
    db.add(cfo)
    db.commit()

def seed_vendors(db: Session):
    print("Seeding vendors...")
    vendors = []
    for _ in range(10):
        vendor = Vendor(
            name=fake.company(),
            rating=round(random.uniform(3.0, 5.0), 1),
            contact_email=fake.company_email(),
            warranty_months=random.choice([12, 24, 36])
        )
        db.add(vendor)
        vendors.append(vendor)
    db.commit()
    return vendors

def seed_products_and_vendor_products(db: Session, vendors: list):
    print("Seeding products...")
    categories = ["Laptop", "Monitor", "Chair", "Desk", "Server", "Software"]
    
    products = []
    for _ in range(50):
        category = random.choice(categories)
        product = Product(
            name=f"{fake.company()} {category}",
            category=category,
            specifications={"brand": fake.company(), "model": fake.word()},
            description=fake.text(max_nb_chars=200)
        )
        db.add(product)
        products.append(product)
    
    db.commit()
    
    print("Seeding vendor_products...")
    for product in products:
        # Each product sold by 1 to 3 random vendors
        num_vendors = random.randint(1, 3)
        selected_vendors = random.sample(vendors, num_vendors)
        
        base_price = random.uniform(100.0, 3000.0)
        
        for vendor in selected_vendors:
            vp = VendorProduct(
                vendor_id=vendor.id,
                product_id=product.id,
                price=round(base_price * random.uniform(0.9, 1.1), 2),
                lead_time_days=random.randint(1, 14)
            )
            db.add(vp)
    
    db.commit()

def run():
    print("Starting database seed...")
    
    # 1. Ensure the pgvector extension is enabled on Supabase
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()

    # 2. Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(Department).first():
            print("Database already seeded. Skipping.")
            return

        depts = seed_departments(db)
        seed_budgets(db, depts)
        seed_users(db, depts)
        vendors = seed_vendors(db)
        seed_products_and_vendor_products(db, vendors)
        
        print("Database seeded successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    run()
