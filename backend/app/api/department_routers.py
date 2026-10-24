
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError
from typing import List

from db.models.department import Department, DepartmentCreate, DepartmentUpdate
from db.repository.department_repo import DepartmentRepository
from db.repository.employee_repo import EmployeeRepository

from db.database import SessionDep


department_router = APIRouter(
    prefix="/department",
    tags=["department"],
)

DUPLICATE_DEPARTMENT = "A department with this id or name already exists"


@department_router.post("/add", response_model=Department, status_code=status.HTTP_201_CREATED)
async def create_department(
    department_data: DepartmentCreate,
    session: SessionDep
):
    try:
        department = Department(**department_data.model_dump())
        return await DepartmentRepository.create_department(session, department)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_DEPARTMENT)


@department_router.get("/get_by_name/{department_name}", response_model=Department)
async def get_department_by_name(
    department_name: str,
    session: SessionDep
):
    department = await DepartmentRepository.get_department_by_name(session, department_name)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    return department


@department_router.get("/{department_id}", response_model=Department)
async def get_department(
    department_id: int,
    session: SessionDep
):
    department = await DepartmentRepository.get_department(session, department_id)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    return department


@department_router.get("/", response_model=List[Department])
async def get_all_departments(session: SessionDep):
    return await DepartmentRepository.get_all_departments(session)


# Only the fields sent in the body are changed
@department_router.put("/update/{department_id}", response_model=Department)
async def update_department(
    department_id: int,
    department_data: DepartmentUpdate,
    session: SessionDep
):
    try:
        department = await DepartmentRepository.update_department(
            session, department_id, department_data.model_dump(exclude_unset=True)
        )
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_DEPARTMENT)
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    return department


@department_router.delete("/del/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: int,
    session: SessionDep
):
    # Deleting a department that still has employees would leave them pointing at nothing
    if await EmployeeRepository.count_in_department(session, department_id) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department still has employees, move or delete them first"
        )
    success = await DepartmentRepository.delete_department(session, department_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
