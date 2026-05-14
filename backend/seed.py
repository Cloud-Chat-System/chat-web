import os
import sys

# Add the server directory to sys.path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, Base, engine
from app.models import User, UserPresence
from app.auth import hash_password

def seed_users():
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    default_users = [
        {
            "username": "admin",
            "email": "admin@tsmc.com",
            "password": "password123",
            "display_name": "系統管理員"
        },
        {
            "username": "alice",
            "email": "alice@tsmc.com",
            "password": "password123",
            "display_name": "Alice"
        },
        {
            "username": "bob",
            "email": "bob@tsmc.com",
            "password": "password123",
            "display_name": "Bob"
        }
    ]
    
    print("開始建立預設使用者...")
    
    for u in default_users:
        # Check if user exists
        existing_user = db.query(User).filter((User.email == u["email"]) | (User.username == u["username"])).first()
        if existing_user:
            print(f"使用者 {u['username']} 已存在，跳過。")
            continue
            
        user = User(
            username=u["username"],
            email=u["email"],
            password_hash=hash_password(u["password"]),
            display_name=u["display_name"],
            auth_provider="local"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create presence
        presence = UserPresence(user_id=user.id, status="offline")
        db.add(presence)
        db.commit()
        
        print(f"成功建立使用者: {u['username']} (Email: {u['email']})")
        
    db.close()
    print("完成！")

if __name__ == "__main__":
    seed_users()
