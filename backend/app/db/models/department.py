
from sqlmodel import Field, SQLModel
from db.models.base import DBBaseModel


class DepartmentBase(SQLModel):
    """Fields a client can send when creating a department."""
    name: str = Field(max_length=50, description="department name")
    parent_id: int = Field(default=0, description="parent department id")
    manager_id: int = Field(default=0, description="department manager id")


class Department(DBBaseModel, DepartmentBase, table=True):
    """
    department model
    """
    __tablename__ = "department"
    # None lets the database assign the next id (AUTOINCREMENT)
    id: int | None = Field(default=None, primary_key=True, index=True, description="department id")


class DepartmentCreate(DepartmentBase):
    id: int | None = Field(default=None, description="optional, assigned automatically when empty")


class DepartmentUpdate(SQLModel):
    """Partial update: only the fields sent are changed."""
    name: str | None = Field(default=None, max_length=50)
    parent_id: int | None = None
    manager_id: int | None = None
