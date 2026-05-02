import { appConfig } from "../config/env";
import type {
  Assignment,
  AssignmentApprovalPayload,
  AssignmentManualCreatePayload,
  Department,
  DepartmentInput,
  Employee,
  EmployeeLeave,
  EmployeeLeaveStatusUpdatePayload,
  EmployeeLeaveInput,
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
  WorkSchedule,
  WorkScheduleDay,
  WorkScheduleDayInput,
  WorkScheduleInput,
} from "../types/api";
import { createJsonClient } from "./http";
import { getAccessToken, refreshAccessToken } from "./auth-service";

const client = createJsonClient(appConfig.coreServiceUrl, {
  defaultCredentials: "include",
  getAccessToken,
  onUnauthorized: refreshAccessToken,
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
    description: "Reusable schedule templates per employee, now read-only for employee-facing flows.",
    nextStep: "Implemented on canonical /schedule with employee read-only visibility and manager/admin workspace CRUD.",
    requiresAuth: true,
  },
  {
    key: "work-schedule-days",
    label: "Work Schedule Days",
    endpoint: "/work-schedule-days/",
    description: "Weekday-level schedule details for planning availability, now read-only for employee-facing flows.",
    nextStep: "Implemented on canonical /schedule with manager/admin day-rule CRUD and employee read-only visibility.",
    requiresAuth: true,
  },
  {
    key: "employee-leaves",
    label: "Employee Leaves",
    endpoint: "/employee-leaves/",
    description: "Employee leave requests with requested-only self-service mutations and manager/admin review queue.",
    nextStep: "Implemented on canonical /leaves with employee self-service and manager/admin requested queue decisions.",
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
    nextStep: "Implemented in point 10: read-only list with local filters and backend-owned business truth.",
    requiresAuth: true,
  },
  {
    key: "approve-proposal",
    label: "Approve Proposal",
    endpoint: "/assignments/approve-proposal/",
    description: "Approval handoff that converts a selected planner proposal into a final assignment.",
    nextStep: "Implemented in point 9: manager action lives on the persisted planning review screen.",
    requiresAuth: true,
  },
  {
    key: "manual-assignment",
    label: "Manual Assignment",
    endpoint: "/assignments/manual/",
    description: "Direct final assignment creation in core-service without planner proposal approval.",
    nextStep: "Implemented in the /tasks/new assignment modal as the manual fallback path.",
    requiresAuth: true,
  },
  {
    key: "reject-assignment",
    label: "Reject Assignment",
    endpoint: "/assignments/{id}/reject/",
    description: "Marks a final assignment as rejected while preserving backend-owned history.",
    nextStep: "Stage 4 should expose this as a manager/admin action on assignment flows.",
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
  listWorkSchedules: () => client.get<WorkSchedule[]>("/work-schedules/"),
  createWorkSchedule: (payload: WorkScheduleInput) => client.post<WorkSchedule>("/work-schedules/", payload),
  updateWorkSchedule: (id: number, payload: WorkScheduleInput) =>
    client.patch<WorkSchedule>(`/work-schedules/${id}/`, payload),
  deleteWorkSchedule: (id: number) => client.delete<null>(`/work-schedules/${id}/`).then(() => undefined),
  listWorkScheduleDays: () => client.get<WorkScheduleDay[]>("/work-schedule-days/"),
  createWorkScheduleDay: (payload: WorkScheduleDayInput) =>
    client.post<WorkScheduleDay>("/work-schedule-days/", payload),
  updateWorkScheduleDay: (id: number, payload: WorkScheduleDayInput) =>
    client.patch<WorkScheduleDay>(`/work-schedule-days/${id}/`, payload),
  deleteWorkScheduleDay: (id: number) =>
    client.delete<null>(`/work-schedule-days/${id}/`).then(() => undefined),
  listEmployeeLeaves: () => client.get<EmployeeLeave[]>("/employee-leaves/"),
  createEmployeeLeave: (payload: EmployeeLeaveInput) =>
    client.post<EmployeeLeave>("/employee-leaves/", payload),
  updateEmployeeLeave: (id: number, payload: EmployeeLeaveInput) =>
    client.patch<EmployeeLeave>(`/employee-leaves/${id}/`, payload),
  deleteEmployeeLeave: (id: number) => client.delete<null>(`/employee-leaves/${id}/`).then(() => undefined),
  setEmployeeLeaveStatus: (id: number, payload: EmployeeLeaveStatusUpdatePayload) =>
    client.post<EmployeeLeave>(`/employee-leaves/${id}/set-status/`, payload),
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
  createManualAssignment: (payload: AssignmentManualCreatePayload) =>
    client.post<Assignment>("/assignments/manual/", payload),
  rejectAssignment: (id: number) => client.post<Assignment>(`/assignments/${id}/reject/`, undefined),
};
