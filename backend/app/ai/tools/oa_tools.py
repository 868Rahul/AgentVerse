from langchain_core.tools import BaseTool, tool

from db.models.employee import Employee
from db.repository.employee_repo import EmployeeRepository
from db.models.department import Department
from db.repository.department_repo import DepartmentRepository
from db.database import async_session_maker
from ai.rag.handbook import handbook_retriever
import logging

logger = logging.getLogger(__name__)

DB_UNAVAILABLE = {"error": "the employee database is currently unavailable, tell the user to try again later"}


@tool
async def get_user_info(user_name: str) -> dict:
    """Look up one employee of the company by name.
    Returns employee number, position, department id, contact details, status (1 trial, 2 active, 3 left) and entry date.
    Use it for questions about a specific colleague, e.g. "What is Jack's position?"."""
    try:
        async with async_session_maker() as session:
            employee =  await EmployeeRepository.get_employee_by_name(session, name=user_name)
    except Exception as e:
        logger.error(f"get_user_info failed: {e}")
        return DB_UNAVAILABLE

    if not employee:
        return {"error": "user not found"}

    return employee.model_dump()

@tool
async def get_user_department(user_name: str) -> dict:
    """Look up the department an employee belongs to, by employee name.
    Use it for questions like "Which department is Jack in?"."""
   
    try:
        async with async_session_maker() as session:
            employee = await EmployeeRepository.get_employee_by_name(session, name=user_name)

            if not employee:
                return {"error": "user not found"}

            department = await DepartmentRepository.get_department(session, department_id=employee.department_id)
    except Exception as e:
        logger.error(f"get_user_department failed: {e}")
        return DB_UNAVAILABLE

    if not department:
        return {"error": "department not found"}

    return department.model_dump()

@tool
async def search_handbook(query: str) -> str:
    """Search the company Employee Handbook (official policies and rules).
    Use it for ANY question about company policy: working hours, attendance, overtime, vacation, holidays,
    sick/personal/parental/bereavement leave, benefits, insurance, retirement, salary, performance review,
    expenses, resignation/termination, harassment, confidentiality, computer and internet use, etc.
    Pass a short, specific search query, e.g. "vacation days accrual"."""
    try:
        results = await handbook_retriever.search(query[:500], k=5)
    except Exception as e:
        logger.error(f"Handbook search failed: {e}")
        return "The employee handbook search is currently unavailable. Tell the user you cannot check the handbook right now."

    if not results:
        return "No matching section was found in the employee handbook."

    return "\n\n---\n\n".join(
        f"(Handbook page {doc.metadata['page']})\n{doc.page_content}" for doc in results
    )


@tool
async def list_handbook_sections() -> str:
    """List the sections (topics) covered by the Employee Handbook.
    Use it when the user asks what the handbook covers or what kind of policy questions they can ask."""
    try:
        sections = await handbook_retriever.sections()
    except Exception as e:
        logger.error(f"Listing handbook sections failed: {e}")
        return "The employee handbook is currently unavailable."
    return "\n".join(sections)
