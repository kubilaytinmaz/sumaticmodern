"""
Add register definitions to database.
Run this inside the Docker container or locally to add register mappings.
"""
import asyncio
import sys
from app.database import async_session_maker
from app.models.register_definition import RegisterDefinition
from sqlalchemy import select


async def add_registers():
    """Add register definitions if they don't exist."""
    async with async_session_maker() as session:
        # Check existing registers
        result = await session.execute(select(RegisterDefinition))
        existing = result.scalars().all()
        
        if existing:
            print(f"Zaten {len(existing)} register tanımı var:")
            for r in existing:
                print(f"  fc={r.fc}, reg={r.reg}, name={r.name}")
            return
        
        # Add register definitions
        registers = [
            RegisterDefinition(fc=4, reg=2000, name='Sayac 1'),  # 19L counter
            RegisterDefinition(fc=4, reg=2001, name='Sayac 2'),  # 5L counter
            RegisterDefinition(fc=3, reg=100, name='Sıcaklık'),
            RegisterDefinition(fc=3, reg=101, name='Basınç'),
            RegisterDefinition(fc=3, reg=102, name='Nem'),
        ]
        
        for reg in registers:
            session.add(reg)
        
        await session.commit()
        print(f"{len(registers)} register tanımı eklendi:")
        for r in registers:
            print(f"  fc={r.fc}, reg={r.reg}, name={r.name}")


if __name__ == "__main__":
    asyncio.run(add_registers())
