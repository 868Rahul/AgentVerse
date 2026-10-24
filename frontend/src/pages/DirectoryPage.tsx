import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  App,
  Button,
  DatePicker,
  Form,
  Input,

  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { Department, DepartmentInput, Employee, EmployeeInput, departmentApi, employeeApi } from "../api";

const GENDERS = [
  { value: 0, label: "Unknown" },
  { value: 1, label: "Male" },
  { value: 2, label: "Female" },
];
const STATUSES = [
  { value: 1, label: "Probation", color: "gold" },
  { value: 2, label: "Active", color: "green" },
  { value: 3, label: "Left", color: "default" },
];

// ---------------------------------------------------------------- employee form

interface EmployeeFormProps {
  open: boolean;
  employee: Employee | null; // null = create
  departments: Department[];
  onClose: () => void;
  onSaved: () => void;
}

const EmployeeForm: React.FC<EmployeeFormProps> = ({ open, employee, departments, onClose, onSaved }) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    form.resetFields();
    form.setFieldsValue(
      employee
        ? { ...employee, entry_date: employee.entry_date ? dayjs(employee.entry_date) : null }
        : { gender: 0, status: 2, department_id: departments[0]?.id, entry_date: dayjs() }
    );
  }, [open, employee]);

  const submit = async () => {
    const values = await form.validateFields();
    const data: EmployeeInput = { ...values, entry_date: values.entry_date.format("YYYY-MM-DD") };
    setSaving(true);
    try {
      if (employee) {
        await employeeApi.update(employee.id, data);
        message.success(`${data.name} updated`);
      } else {
        await employeeApi.create(data);
        message.success(`${data.name} added`);
      }
      onSaved();
      onClose();
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title={employee ? `Edit ${employee.name}` : "Add employee"}
      okText={employee ? "Save" : "Add employee"}
      confirmLoading={saving}
      onOk={submit}
      onCancel={onClose}
      destroyOnHidden
      width={640}
    >
      <Form form={form} layout="vertical" requiredMark="optional" className="mt-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4">
          <Form.Item name="name" label="Full name" rules={[{ required: true, max: 50 }]}>
            <Input placeholder="e.g. Priya Sharma" />
          </Form.Item>
          <Form.Item name="employee_no" label="Employee number" rules={[{ required: true, max: 50 }]}>
            <Input placeholder="e.g. E-1024" />
          </Form.Item>
          <Form.Item name="email" label="Email" rules={[{ required: true, type: "email", max: 50 }]}>
            <Input placeholder="name@company.com" />
          </Form.Item>
          <Form.Item
            name="phone"
            label="Phone"
            rules={[{ required: true, pattern: /^\+?\d{6,11}$/, message: "Digits only, max 11" }]}
          >
            <Input placeholder="9876543210" />
          </Form.Item>
          <Form.Item name="position" label="Position" rules={[{ required: true, max: 50 }]}>
            <Input placeholder="e.g. Developer" />
          </Form.Item>
          <Form.Item name="department_id" label="Department" rules={[{ required: true }]}>
            <Select options={departments.map((d) => ({ value: d.id, label: d.name }))} placeholder="Select" />
          </Form.Item>
          <Form.Item name="gender" label="Gender" rules={[{ required: true }]}>
            <Select options={GENDERS} />
          </Form.Item>
          <Form.Item name="status" label="Status" rules={[{ required: true }]}>
            <Select options={STATUSES.map(({ value, label }) => ({ value, label }))} />
          </Form.Item>
          <Form.Item name="entry_date" label="Entry date" rules={[{ required: true }]}>
            <DatePicker className="w-full" />
          </Form.Item>
        </div>
      </Form>
    </Modal>
  );
};

// ---------------------------------------------------------------- department form

interface DepartmentFormProps {
  open: boolean;
  department: Department | null;
  departments: Department[];
  employees: Employee[];
  onClose: () => void;
  onSaved: () => void;
}

const DepartmentForm: React.FC<DepartmentFormProps> = ({ open, department, departments, employees, onClose, onSaved }) => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    form.resetFields();
    form.setFieldsValue(department ?? { parent_id: 0, manager_id: 0 });
  }, [open, department]);

  const submit = async () => {
    const values: DepartmentInput = await form.validateFields();
    setSaving(true);
    try {
      if (department) {
        await departmentApi.update(department.id, values);
        message.success(`${values.name} updated`);
      } else {
        await departmentApi.create(values);
        message.success(`${values.name} added`);
      }
      onSaved();
      onClose();
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title={department ? `Edit ${department.name}` : "Add department"}
      okText={department ? "Save" : "Add department"}
      confirmLoading={saving}
      onOk={submit}
      onCancel={onClose}
      destroyOnHidden
    >
      <Form form={form} layout="vertical" requiredMark="optional" className="mt-4">
        <Form.Item name="name" label="Name" rules={[{ required: true, max: 50 }]}>
          <Input placeholder="e.g. Finance" />
        </Form.Item>
        <Form.Item name="parent_id" label="Parent department">
          <Select
            options={[
              { value: 0, label: "None (top level)" },
              ...departments.filter((d) => d.id !== department?.id).map((d) => ({ value: d.id, label: d.name })),
            ]}
          />
        </Form.Item>
        <Form.Item name="manager_id" label="Manager">
          <Select
            showSearch
            optionFilterProp="label"
            options={[{ value: 0, label: "Not set" }, ...employees.map((e) => ({ value: e.id, label: e.name }))]}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

// ---------------------------------------------------------------- page

const DirectoryPage: React.FC = () => {
  const { message } = App.useApp();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [employeeForm, setEmployeeForm] = useState<{ open: boolean; employee: Employee | null }>({ open: false, employee: null });
  const [departmentForm, setDepartmentForm] = useState<{ open: boolean; department: Department | null }>({
    open: false,
    department: null,
  });

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [employeeList, departmentList] = await Promise.all([employeeApi.list(), departmentApi.list()]);
      setEmployees(employeeList);
      setDepartments(departmentList);
    } catch (e: any) {
      message.error(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const departmentName = (id: number) => departments.find((d) => d.id === id)?.name ?? "—";
  const employeeName = (id: number) => employees.find((e) => e.id === id)?.name ?? "—";

  const filteredEmployees = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return employees;
    return employees.filter((e) =>
      [e.name, e.email, e.position, e.employee_no, departmentName(e.department_id)].some((v) => v?.toLowerCase().includes(q))
    );
  }, [employees, departments, search]);

  const removeEmployee = async (employee: Employee) => {
    try {
      await employeeApi.remove(employee.id);
      message.success(`${employee.name} deleted`);
      reload();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const removeDepartment = async (department: Department) => {
    try {
      await departmentApi.remove(department.id);
      message.success(`${department.name} deleted`);
      reload();
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const employeeColumns: ColumnsType<Employee> = [
    { title: "No.", dataIndex: "employee_no", width: 90, sorter: (a, b) => a.employee_no.localeCompare(b.employee_no) },
    {
      title: "Name",
      dataIndex: "name",
      sorter: (a, b) => a.name.localeCompare(b.name),
      render: (name: string, e) => (
        <div>
          <div className="font-medium text-slate-800 capitalize">{name}</div>
          <div className="text-xs text-slate-400">{e.email}</div>
        </div>
      ),
    },
    { title: "Position", dataIndex: "position", responsive: ["md"] },
    {
      title: "Department",
      dataIndex: "department_id",
      render: (id: number) => departmentName(id),
      filters: departments.map((d) => ({ text: d.name, value: d.id })),
      onFilter: (value, e) => e.department_id === value,
    },
    { title: "Phone", dataIndex: "phone", responsive: ["lg"] },
    {
      title: "Status",
      dataIndex: "status",
      render: (status: number) => {
        const s = STATUSES.find((x) => x.value === status);
        return <Tag color={s?.color}>{s?.label ?? "Unknown"}</Tag>;
      },
    },
    { title: "Joined", dataIndex: "entry_date", responsive: ["lg"], sorter: (a, b) => a.entry_date.localeCompare(b.entry_date) },
    {
      title: "",
      key: "actions",
      width: 96,
      render: (_, employee) => (
        <Space size={0}>
          <Button
            type="text"
            icon={<EditOutlined />}
            aria-label={`Edit ${employee.name}`}
            onClick={() => setEmployeeForm({ open: true, employee })}
          />
          <Popconfirm
            title={`Delete ${employee.name}?`}
            okText="Delete"
            okButtonProps={{ danger: true }}
            onConfirm={() => removeEmployee(employee)}
          >
            <Button type="text" danger icon={<DeleteOutlined />} aria-label={`Delete ${employee.name}`} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const departmentColumns: ColumnsType<Department> = [
    { title: "ID", dataIndex: "id", width: 70 },
    { title: "Name", dataIndex: "name", render: (name: string) => <span className="font-medium text-slate-800">{name}</span> },
    { title: "Parent", dataIndex: "parent_id", render: (id: number) => (id ? departmentName(id) : "—") },
    { title: "Manager", dataIndex: "manager_id", render: (id: number) => (id ? employeeName(id) : "—") },
    {
      title: "Employees",
      key: "count",
      render: (_, d) => employees.filter((e) => e.department_id === d.id).length,
    },
    {
      title: "",
      key: "actions",
      width: 96,
      render: (_, department) => (
        <Space size={0}>
          <Button
            type="text"
            icon={<EditOutlined />}
            aria-label={`Edit ${department.name}`}
            onClick={() => setDepartmentForm({ open: true, department })}
          />
          <Popconfirm
            title={`Delete ${department.name}?`}
            okText="Delete"
            okButtonProps={{ danger: true }}
            onConfirm={() => removeDepartment(department)}
          >
            <Button type="text" danger icon={<DeleteOutlined />} aria-label={`Delete ${department.name}`} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const stats = [
    { label: "Employees", value: employees.length },
    { label: "Active", value: employees.filter((e) => e.status === 2).length },
    { label: "Departments", value: departments.length },
  ];

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="grid grid-cols-3 gap-3 mb-6">
          {stats.map((s) => (
            <div key={s.label} className="rounded-xl border border-slate-200 bg-white px-4 py-3">
              <div className="text-xs text-slate-500">{s.label}</div>
              <div className="text-2xl font-semibold text-slate-800 tabular-nums">{s.value}</div>
            </div>
          ))}
        </div>

        <div className="rounded-xl border border-slate-200 bg-white px-4 pb-2">
          <Tabs
            defaultActiveKey="employees"
            tabBarExtraContent={
              <Button icon={<ReloadOutlined />} onClick={reload} aria-label="Reload" type="text" />
            }
            items={[
              {
                key: "employees",
                label: "Employees",
                children: (
                  <>
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                      <Input
                        allowClear
                        prefix={<SearchOutlined className="text-slate-400" />}
                        placeholder="Search name, email, position…"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="max-w-xs"
                      />
                      <Button type="primary" icon={<PlusOutlined />} onClick={() => setEmployeeForm({ open: true, employee: null })}>
                        Add employee
                      </Button>
                    </div>
                    <Table
                      rowKey="id"
                      size="middle"
                      loading={loading}
                      columns={employeeColumns}
                      dataSource={filteredEmployees}
                      pagination={{ pageSize: 10, hideOnSinglePage: true }}
                      scroll={{ x: true }}
                      locale={{ emptyText: search ? "No employee matches your search" : "No employees yet" }}
                    />
                  </>
                ),
              },
              {
                key: "departments",
                label: "Departments",
                children: (
                  <>
                    <div className="flex justify-end mb-3">
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setDepartmentForm({ open: true, department: null })}
                      >
                        Add department
                      </Button>
                    </div>
                    <Table
                      rowKey="id"
                      size="middle"
                      loading={loading}
                      columns={departmentColumns}
                      dataSource={departments}
                      pagination={false}
                      scroll={{ x: true }}
                    />
                  </>
                ),
              },
            ]}
          />
        </div>
      </div>

      <EmployeeForm
        open={employeeForm.open}
        employee={employeeForm.employee}
        departments={departments}
        onClose={() => setEmployeeForm({ open: false, employee: null })}
        onSaved={reload}
      />
      <DepartmentForm
        open={departmentForm.open}
        department={departmentForm.department}
        departments={departments}
        employees={employees}
        onClose={() => setDepartmentForm({ open: false, department: null })}
        onSaved={reload}
      />
    </div>
  );
};

export default DirectoryPage;
