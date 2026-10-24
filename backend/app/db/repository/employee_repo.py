from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

from db.models.employee import Employee


class EmployeeRepository:

    @classmethod
    async def _commit(cls, session: AsyncSession) -> None:
        """Commit, and undo the session on constraint errors (e.g. duplicate employee_no)."""
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise

    @classmethod
    async def create_employee(cls, session: AsyncSession, employee: Employee) -> Employee:
        session.add(employee)
        await cls._commit(session)
        await session.refresh(employee)
        return employee

    @classmethod
    async def get_employee(cls, session: AsyncSession, employee_id: int) -> Optional[Employee]:
        result = await session.execute(
            select(Employee).where(Employee.id == employee_id)
        )
        return result.scalars().first()

    # Get employee information by employee name
    @classmethod
    async def get_employee_by_name(cls, session: AsyncSession, name: str) -> Optional[Employee]:
        result = await session.execute(
            select(Employee).where(func.lower(Employee.name) == name.strip().lower())
        )
        return result.scalars().first()

    @classmethod
    async def get_all_employees(cls, session: AsyncSession) -> List[Employee]:
        result = await session.execute(select(Employee).order_by(Employee.id))
        return result.scalars().all()

    @classmethod
    async def count_in_department(cls, session: AsyncSession, department_id: int) -> int:
        result = await session.execute(
            select(func.count()).select_from(Employee).where(Employee.department_id == department_id)
        )
        return result.scalar_one()

    @classmethod
    async def update_employee(cls, session: AsyncSession, employee_id: int, employee_data: dict) -> Optional[Employee]:
        employee = await cls.get_employee(session, employee_id)
        if employee:
            for key, value in employee_data.items():
                setattr(employee, key, value)
            employee.edit_time = datetime.now()
            await cls._commit(session)
            await session.refresh(employee)
        return employee

    @classmethod
    async def delete_employee(cls, session: AsyncSession, employee_id: int) -> bool:
        employee = await cls.get_employee(session, employee_id)
        if employee:
            await session.delete(employee)
            await session.commit()
            return True
        return False
