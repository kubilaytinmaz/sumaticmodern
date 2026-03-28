"""
Create initial admin user for development.
Run: cd backend && python -m app.create_admin
"""
import asyncio
from app.database import async_session_maker, init_db
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select


async def create_admin():
    """Create admin user if not exists."""
    # Initialize tables
    await init_db()
    
    async with async_session_maker() as session:
        # Check if admin already exists
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"Admin user already exists (id={existing.id})")
            return
        
        # Create admin user
        admin = User(
            username="admin",
            email="admin@sumatic.io",
            password_hash=get_password_hash("admin123"),
            full_name="Admin User",
            role="admin",
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        
        print(f"Admin user created!")
        print(f"  Username: admin")
        print(f"  Password: admin123")
        print(f"  Role: admin")
        print(f"  ID: {admin.id}")


if __name__ == "__main__":
    asyncio.run(create_admin())
