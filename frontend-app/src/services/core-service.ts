import { appConfig } from "../config/env";
import type {
  Assignment,
  AssignmentApprovalPayload,
  Department,
  Employee,
  ResourceDescriptor,
  Skill,
  Task,
  TaskRequirement,
  User,
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
    nextStep: "Add authenticated list and create form.",
    requiresAuth: true,
  },
  {
    key: "departments",
    label: "Departments",
    endpoint: "/departments/",
    description: "Reference grouping for employees and tasks.",
    nextStep: "Add list/create/edit CRUD with lightweight validation.",
    requiresAuth: true,
  },
  {
    key: "skills",
    label: "Skills",
    endpoint: "/skills/",
    description: "Shared vocabulary for task requirements and employee capabilities.",
    nextStep: "Add list/create/edit CRUD before employee skill linking.",
    requiresAuth: true,
  },
  {
    key: "employees",
    label: "Employees",
    endpoint: "/employees/",
    description: "Business employee profiles linked to users and departments.",
    nextStep: "Add create/edit form after reference dictionaries are ready.",
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
    nextStep: "Add create/list flow with explicit due-date validation.",
    requiresAuth: true,
  },
  {
    key: "task-requirements",
    label: "Task Requirements",
    endpoint: "/task-requirements/",
    description: "Skill requirements that planner scoring and eligibility use.",
    nextStep: "Add task-linked requirements editor after task form exists.",
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
  createUser: (payload: Partial<User> & { password?: string }) => client.post<User>("/users/", payload),
  listDepartments: () => client.get<Department[]>("/departments/"),
  createDepartment: (payload: Pick<Department, "name" | "description">) =>
    client.post<Department>("/departments/", payload),
  listSkills: () => client.get<Skill[]>("/skills/"),
  createSkill: (payload: Pick<Skill, "name" | "description">) => client.post<Skill>("/skills/", payload),
  listEmployees: () => client.get<Employee[]>("/employees/"),
  createEmployee: (payload: Omit<Employee, "id" | "created_at" | "updated_at">) =>
    client.post<Employee>("/employees/", payload),
  listTasks: () => client.get<Task[]>("/tasks/"),
  createTask: (payload: Omit<Task, "id" | "created_at" | "updated_at">) => client.post<Task>("/tasks/", payload),
  listTaskRequirements: () => client.get<TaskRequirement[]>("/task-requirements/"),
  createTaskRequirement: (payload: Omit<TaskRequirement, "id">) =>
    client.post<TaskRequirement>("/task-requirements/", payload),
  listAssignments: () => client.get<Assignment[]>("/assignments/"),
  approveProposal: (payload: AssignmentApprovalPayload) =>
    client.post<Assignment>("/assignments/approve-proposal/", payload),
};
