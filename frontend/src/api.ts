// Backend URL, configured in .env.local (VITE_API_BASE_URL)
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface Employee {
  id: number;
  employee_no: string;
  name: string;
  gender: number;
  department_id: number;
  position: string;
  phone: string;
  email: string;
  status: number;
  entry_date: string;
  create_time?: string;
  edit_time?: string;
}

export interface Department {
  id: number;
  name: string;
  parent_id: number;
  manager_id: number;
  create_time?: string;
  edit_time?: string;
}

export type EmployeeInput = Omit<Employee, "id" | "create_time" | "edit_time">;
export type DepartmentInput = Omit<Department, "id" | "create_time" | "edit_time">;

/** fetch wrapper: throws an Error with the backend's `detail` message on failure */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch (e) {
    throw new Error("Cannot reach the backend. Is the server running on " + API_BASE_URL + "?");
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: any) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join(", ");
    } catch {
      // body was not JSON
    }
    throw new Error(detail);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const employeeApi = {
  list: () => request<Employee[]>("/employee/get_all"),
  create: (data: EmployeeInput) => request<Employee>("/employee/add", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: Partial<EmployeeInput>) =>
    request<Employee>(`/employee/update/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  remove: (id: number) => request<void>(`/employee/delete/${id}`, { method: "DELETE" }),
};

export const departmentApi = {
  list: () => request<Department[]>("/department/"),
  create: (data: DepartmentInput) => request<Department>("/department/add", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: Partial<DepartmentInput>) =>
    request<Department>(`/department/update/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  remove: (id: number) => request<void>(`/department/del/${id}`, { method: "DELETE" }),
};
