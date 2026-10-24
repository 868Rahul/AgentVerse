from db.models.base import DBBaseModel
from sqlmodel import Field, SQLModel


class EmployeeBase(SQLModel):
    """Fields a client can send when creating an employee."""
    employee_no: str = Field(max_length=50, description="employee no")
    name: str = Field(max_length=50, index=True, description="employee name")
    gender: int = Field(default=0, ge=0, le=2, description="gender: 0-unknown 1-male 2-female")
    department_id: int = Field(default=0, description="department id")
    position: str = Field(max_length=50, description="position")
    phone: str = Field(max_length=11, description="phone")
    email: str = Field(max_length=50, description="email")
    status: int = Field(default=2, ge=1, le=3, description="status: 1-trial 2-active 3-terminated")
    entry_date: str = Field(max_length=50, description="entry date")


class Employee(DBBaseModel, EmployeeBase, table=True):
    """
    employee model
    """
    __tablename__ = "employee"
    # None lets the database assign the next id (AUTOINCREMENT)
    id: int | None = Field(default=None, primary_key=True, index=True, description="employee id")


class EmployeeCreate(EmployeeBase):
    id: int | None = Field(default=None, description="optional, assigned automatically when empty")


class EmployeeUpdate(SQLModel):
    """Partial update: only the fields sent are changed."""
    employee_no: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, max_length=50)
    gender: int | None = Field(default=None, ge=0, le=2)
    department_id: int | None = None
    position: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=11)
    email: str | None = Field(default=None, max_length=50)
    status: int | None = Field(default=None, ge=1, le=3)
    entry_date: str | None = Field(default=None, max_length=50)
