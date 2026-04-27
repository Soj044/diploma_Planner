import { appConfig } from "../config/env";
import type {
  Assignment,
  AssignmentApprovalPayload,
  Department,
  DepartmentInput,
  Employee,
  EmployeeInput,
  ResourceDescriptor,
  Skill,
  SkillInput,
  Task,
  TaskInput,
  TaskRequirement,
  TaskRequirementInput,
  User,
  UserInput,
} from "../types/api";
import { createJsonClient } from "./http";

const client = createJsonClient(appConfig.coreServiceUrl, {
  authHeader: appConfig.coreServiceAuthHeader,
});

export const referenceDataResources: ResourceDescriptor[] = [
  {
    key: "users",
    label: "Users",
    endpoint: "/users/",
    description: "Source accounts for managers and employees.",
    nextStep: "Implemented in point 5: list, create, edit, and delete.",
    requiresAuth: true,
  },
  {
    key: "departments",
    label: "Departments",
    endpoint: "/departments/",
    description: "Reference grouping for employees and tasks.",
    nextStep: "Implemented in point 5: list, create, edit, and delete.",
    requiresAuth: true,
  },
  {
    key: "skills",
    label: "Skills",
    endpoint: "/skills/",
    description: "Shared vocabulary for task requirements and employee capabilities.",
    nextStep: "Implemented in point 5: list, create, edit, and delete.",
    requiresAuth: true,
  },
  {
    key: "employees",
    label: "Employees",
    endpoint: "/employees/",
    description: "Business employee profiles linked to users and departments.",
    nextStep: "Implemented in point 5: list, create, edit, and delete.",
    requiresAuth: true,
  },
  {
    key: "employee-skills",
    label: "Employee Skills",
    endpoint: "/employee-skills/",
    description: "Many-to-many mapping between employees and skills with levels.",
    nextStep: "Add relation editor after employee and skill screens exist.",
    requiresAuth: true,
  },
  {
    key: "work-schedules",
    label: "Work Schedules",
    endpoint: "/work-schedules/",
    description: "Reusable schedule templates per employee.",
    nextStep: "Add list/create form before daily schedule editing.",
    requiresAuth: true,
  },
  {
    key: "work-schedule-days",
    label: "Work Schedule Days",
    endpoint: "/work-schedule-days/",
    description: "Weekday-level schedule details for planning availability.",
    nextStep: "Add inline editing against an existing schedule.",
    requiresAuth: true,
  },
  {
    key: "employee-leaves",
    label: "Employee Leaves",
    endpoint: "/employee-leaves/",
    description: "Approved leave periods that become hard planner constraints.",
    nextStep: "Add CRUD with date-range validation feedback.",
    requiresAuth: true,
  },
  {
    key: "availability-overrides",
    label: "Availability Overrides",
    endpoint: "/availability-overrides/",
    description: "Date-specific capacity overrides on top of schedules.",
    nextStep: "Add compact form with employee/date picker.",
    requiresAuth: true,
  },
];

export const taskResources: ResourceDescriptor[] = [
  {
    key: "tasks",
    label: "Tasks",
    endpoint: "/tasks/",
    description: "Core operational tasks that feed planner snapshots.",
    nextStep: "Implemented in point 6: list, create, edit, delete, and requirements handoff.",
    requiresAuth: true,
  },
  {
    key: "task-requirements",
    label: "Task Requirements",
    endpoint: "/task-requirements/",
    description: "Skill requirements that planner scoring and eligibility use.",
    nextStep: "Implemented in point 6: task-linked list, create, edit, and delete.",
    requiresAuth: true,
  },
];

export const assignmentResources: ResourceDescriptor[] = [
  {
    key: "assignments",
    label: "Assignments",
    endpoint: "/assignments/",
    description: "Final approved assignments stored only in core-service.",
    nextStep: "Add read-only list first, then filtered detail cards.",
    requiresAuth: true,
  },
  {
    key: "approve-proposal",
    label: "Approve Proposal",
    endpoint: "/assignments/approve-proposal/",
    description: "Approval handoff that converts a selected planner proposal into a final assignment.",
    nextStep: "Add explicit manager action from persisted proposal review.",
    requiresAuth: true,
  },
];

export const coreService = {
  listUsers: () => client.get<User[]>("/users/"),
  createUser: (payload: UserInput) => client.post<User>("/users/", payload),
  updateUser: (id: number, payload: UserInput) => client.patch<User>(`/users/${id}/`, payload),
  deleteUser: (id: number) => client.delete<null>(`/users/${id}/`).then(() => undefined),
  listDepartments: () => client.get<Department[]>("/departments/"),
  createDepartment: (payload: DepartmentInput) => client.post<Department>("/departments/", payload),
  updateDepartment: (id: number, payload: DepartmentInput) =>
    client.patch<Department>(`/departments/${id}/`, payload),
  deleteDepartment: (id: number) => client.delete<null>(`/departments/${id}/`).then(() => undefined),
  listSkills: () => client.get<Skill[]>("/skills/"),
  createSkill: (payload: SkillInput) => client.post<Skill>("/skills/", payload),
  updateSkill: (id: number, payload: SkillInput) => client.patch<Skill>(`/skills/${id}/`, payload),
  deleteSkill: (id: number) => client.delete<null>(`/skills/${id}/`).then(() => undefined),
  listEmployees: () => client.get<Employee[]>("/employees/"),
  createEmployee: (payload: EmployeeInput) => client.post<Employee>("/employees/", payload),
  updateEmployee: (id: number, payload: EmployeeInput) => client.patch<Employee>(`/employees/${id}/`, payload),
  deleteEmployee: (id: number) => client.delete<null>(`/employees/${id}/`).then(() => undefined),
  listTasks: () => client.get<Task[]>("/tasks/"),
  createTask: (payload: TaskInput) => client.post<Task>("/tasks/", payload),
  updateTask: (id: number, payload: TaskInput) => client.patch<Task>(`/tasks/${id}/`, payload),
  deleteTask: (id: number) => client.delete<null>(`/tasks/${id}/`).then(() => undefined),
  listTaskRequirements: () => client.get<TaskRequirement[]>("/task-requirements/"),
  createTaskRequirement: (payload: TaskRequirementInput) =>
    client.post<TaskRequirement>("/task-requirements/", payload),
  updateTaskRequirement: (id: number, payload: TaskRequirementInput) =>
    client.patch<TaskRequirement>(`/task-requirements/${id}/`, payload),
  deleteTaskRequirement: (id: number) =>
    client.delete<null>(`/task-requirements/${id}/`).then(() => undefined),
  listAssignments: () => client.get<Assignment[]>("/assignments/"),
  approveProposal: (payload: AssignmentApprovalPayload) =>
    client.post<Assignment>("/assignments/approve-proposal/", payload),
};
