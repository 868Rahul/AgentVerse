from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError
from db.models.employee import Employee, EmployeeCreate, EmployeeUpdate
from db.repository.employee_repo import EmployeeRepository
from db.database import SessionDep
from typing import List

employee_router = APIRouter(prefix="/employee", tags=["employee"])

DUPLICATE_EMPLOYEE = "An employee with this id or employee number already exists"


# Add an employee
@employee_router.post("/add", response_model=Employee, status_code=status.HTTP_201_CREATED)
async def add_employee(employee_data: EmployeeCreate, session: SessionDep):
    try:
        employee = Employee(**employee_data.model_dump())
        return await EmployeeRepository.create_employee(session, employee)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_EMPLOYEE)


# Get employee information
@employee_router.get("/get/{employee_id}", response_model=Employee)
async def get_employee(employee_id: int, session: SessionDep):
    employee = await EmployeeRepository.get_employee(session, employee_id)
    if employee:
        return employee
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

# Get all employee information
@employee_router.get("/get_all", response_model=List[Employee])
async def get_all_employees(session: SessionDep):
    return await EmployeeRepository.get_all_employees(session)


# Update employee information, only the fields sent in the body are changed
@employee_router.put("/update/{employee_id}", response_model=Employee)
async def update_employee(employee_id: int, employee_data: EmployeeUpdate, session: SessionDep):
    try:
        employee = await EmployeeRepository.update_employee(
            session, employee_id, employee_data.model_dump(exclude_unset=True)
        )
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_EMPLOYEE)
    if employee:
        return employee
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

# Delete employee information
@employee_router.delete("/delete/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(employee_id: int, session: SessionDep):
    success = await EmployeeRepository.delete_employee(session, employee_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")


# Get employee information by name
@employee_router.get("/get_by_name/{name}", response_model=Employee)
async def get_employee_by_name(name: str, session: SessionDep):
    employee = await EmployeeRepository.get_employee_by_name(session, name)
    if employee:
        return employee
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
