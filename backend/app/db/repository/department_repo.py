from datetime import datetime
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List, Optional
from db.models.department import Department


class DepartmentRepository:

    @classmethod
    async def _commit(cls, session: AsyncSession) -> None:
        """Commit, and undo the session on constraint errors (e.g. duplicate department name)."""
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise

    @classmethod
    async def create_department(cls, session: AsyncSession, department: Department) -> Department:
        session.add(department)
        await cls._commit(session)
        await session.refresh(department)
        return department

    @classmethod
    async def get_department(cls, session: AsyncSession, department_id: int) -> Optional[Department]:
        result = await session.execute(
            select(Department).where(Department.id == department_id)
        )
        return result.scalars().first()

    @classmethod
    async def get_department_by_name(cls, session: AsyncSession, name: str) -> Optional[Department]:
        result = await session.execute(
            select(Department).where(func.lower(Department.name) == name.strip().lower())
        )
        return result.scalars().first()

    @classmethod
    async def get_all_departments(cls, session: AsyncSession) -> List[Department]:
        result = await session.execute(select(Department).order_by(Department.id))
        return result.scalars().all()

    @classmethod
    async def update_department(cls, session: AsyncSession, department_id: int, department_data: dict) -> Optional[Department]:
        department = await cls.get_department(session, department_id)
        if department:
            for key, value in department_data.items():
                setattr(department, key, value)
            department.edit_time = datetime.now()
            await cls._commit(session)
            await session.refresh(department)
        return department

    @classmethod
    async def delete_department(cls, session: AsyncSession, department_id: int) -> bool:
        department = await cls.get_department(session, department_id)
        if department:
            await session.delete(department)
            await session.commit()
            return True
        return False
