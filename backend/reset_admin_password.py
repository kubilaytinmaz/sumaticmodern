"""
Reset admin password to admin123
"""
import asyncio
from app.database import async_session_maker
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select


async def reset_admin_password():
    """Reset admin password to admin123."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.username == 'admin')
        )
        user = result.scalar_one_or_none()

        if user:
            user.password_hash = get_password_hash('admin123')
            await session.commit()
            print(f'Admin password reset to admin123 for user: {user.username}')
        else:
            print('Admin user not found')


if __name__ == '__main__':
    asyncio.run(reset_admin_password())
