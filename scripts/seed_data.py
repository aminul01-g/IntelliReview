"""Seed database with sample data."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.database import SessionLocal
from api.models.user import User
from api.auth import get_password_hash

def seed_users():
    """Create sample users."""
    db = SessionLocal()
    
    users = [
        {
            "username": "admin",
            "email": "admin@intellireview.com",
            "password": "admin123",
            "is_superuser": True
        },
        {
            "username": "demo",
            "email": "demo@intellireview.com",
            "password": "demo123",
            "is_superuser": False
        }
    ]
    
    for user_data in users:
        # Check if user exists
        existing = db.query(User).filter(
            User.username == user_data["username"]
        ).first()
        
        if not existing:
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                is_superuser=user_data["is_superuser"]
            )
            db.add(user)
            print(f"Created user: {user_data['username']}")
    
    db.commit()
    db.close()
    print("Database seeded successfully!")

if __name__ == "__main__":
    seed_users()
