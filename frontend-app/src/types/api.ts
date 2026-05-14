export interface ResourceDescriptor {
  key: string;
  label: string;
  endpoint: string;
  description: string;
  nextStep: string;
  requiresAuth?: boolean;
}

export interface WorkflowStepDescriptor {
  title: string;
  details: string;
}

export type AuthRole = "admin" | "manager" | "employee";

export interface AuthEmployeeProfile {
  id: number;
  full_name: string;
  department_id: number | null;
  position_name: string;
  hire_date: string | null;
  is_active: boolean;
}

export interface AuthUser {
  id: number;
  email: string;
  role: AuthRole;
  is_active: boolean;
  employee_id: number | null;
  employee_profile: AuthEmployeeProfile | null;
}

export interface AuthResponse {
  access: string;
  user: AuthUser;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  username?: string;
  first_name?: string;
  last_name?: string;
}

export interface UserInput {
  email: string;
  username: string;
  password?: string;
  first_name: string;
  last_name: string;
  role: string;
  is_active: boolean;
}

export interface User {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  role: string;
  is_active: boolean;
  last_login: string | null;
  date_joined: string;
  updated_at: string;
}

export interface DepartmentInput {
  name: string;
  description: string;
}

export interface DepartmentEmployeeSummary {
  id: number;
  full_name: string;
  position_name: string;
}

export interface Department {
  id: number;
  name: string;
  description: string;
  employees: DepartmentEmployeeSummary[];
  created_at: string;
  updated_at: string;
}

export interface SkillInput {
  name: string;
  description: string;
}

export interface Skill {
  id: number;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface EmployeeInput {
  user: number;
  department: number | null;
  full_name: string;
  position_name: string;
  employment_type: string;
  weekly_capacity_hours: number;
  timezone: string;
  hire_date: string | null;
  is_active: boolean;
}

export interface Employee {
  id: number;
  user: number;
  department: number | null;
  full_name: string;
  position_name: string;
  employment_type: string;
  weekly_capacity_hours: number;
  timezone: string;
  hire_date: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmployeeSkill {
  id: number;
  employee: number;
  skill: number;
  level: number;
  created_at: string;
  updated_at: string;
}

export interface WorkScheduleInput {
  employee: number;
  name: string;
  is_default: boolean;
}

export interface WorkSchedule {
  id: number;
  employee: number;
  name: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkScheduleDayInput {
  schedule: number;
  weekday: number;
  is_working_day: boolean;
  capacity_hours: number;
  start_time: string | null;
  end_time: string | null;
}

export interface WorkScheduleDay {
  id: number;
  schedule: number;
  weekday: number;
  is_working_day: boolean;
  capacity_hours: number;
  start_time: string | null;
  end_time: string | null;
}

export interface SchedulePreviewRule {
  is_working_day: boolean;
  capacity_hours: number;
  start_time: string | null;
  end_time: string | null;
}

export interface SchedulePreviewEffectiveDay extends SchedulePreviewRule {
  source: "schedule" | "approved_leave" | "availability_override" | "no_rule";
}

export interface SchedulePreviewLeaveSummary {
  id: number;
  leave_type: string;
  start_date: string;
  end_date: string;
}

export interface SchedulePreviewAvailabilityOverride {
  id: number;
  date: string;
  available_hours: number;
  reason: string;
}

export interface SchedulePreviewDay {
  date: string;
  weekday: number;
  weekday_label: string;
  base_rule: SchedulePreviewRule | null;
  effective_day: SchedulePreviewEffectiveDay;
  approved_leave: SchedulePreviewLeaveSummary | null;
  availability_override: SchedulePreviewAvailabilityOverride | null;
}

export interface SchedulePreviewSummaryEmployee {
  id: number;
  full_name: string;
  position_name: string;
  department_id: number | null;
  department_name: string | null;
}

export interface SchedulePreviewSummarySchedule {
  id: number;
  name: string;
  is_default: boolean;
}

export interface SchedulePreviewResponse {
  employee: SchedulePreviewSummaryEmployee;
  schedule: SchedulePreviewSummarySchedule | null;
  week_start: string;
  week_end: string;
  days: SchedulePreviewDay[];
}

export interface EmployeeLeaveInput {
  employee: number;
  leave_type: string;
  status?: string;
  start_date: string;
  end_date: string;
  comment: string;
}

export interface EmployeeLeave {
  id: number;
  employee: number;
  leave_type: string;
  status: string;
  start_date: string;
  end_date: string;
  comment: string;
  created_at: string;
  updated_at: string;
}

export interface TaskInput {
  department: number | null;
  title: string;
  description: string;
  status: string;
  priority: string;
  estimated_hours: number | null;
  actual_hours: number | null;
  start_date: string | null;
  due_date: string;
  created_by_user: number;
}

export interface Task {
  id: number;
  department: number | null;
  title: string;
  description: string;
  status: string;
  priority: string;
  estimated_hours: number | null;
  actual_hours: number | null;
  start_date: string | null;
  due_date: string;
  created_by_user: number;
  created_at: string;
  updated_at: string;
}

export interface TaskRequirementInput {
  task: number;
  skill: number;
  min_level: number;
  weight: string;
}

export interface TaskRequirement {
  id: number;
  task: number;
  skill: number;
  min_level: number;
  weight: string;
}

export interface Assignment {
  id: number;
  task: number;
  employee: number;
  source_plan_run_id: string | null;
  planned_hours: number;
  start_date: string;
  end_date: string;
  status: string;
  assigned_by_type: string;
  assigned_by_user: number | null;
  approved_by_user: number | null;
  assigned_at: string;
  approved_at: string | null;
  notes: string;
}

export interface AssignmentApprovalPayload {
  task: number;
  employee: number;
  source_plan_run_id: string;
  notes?: string;
}

export interface AssignmentManualCreatePayload {
  task: number;
  employee: number;
  planned_hours: number;
  notes?: string;
}

export interface EmployeeLeaveStatusUpdatePayload {
  status: "approved" | "rejected";
}

export interface CreatePlanRunRequest {
  planning_period_start: string;
  planning_period_end: string;
  initiated_by_user_id: string;
  department_id?: string | null;
  task_ids: string[];
}

export interface AssignmentProposal {
  task_id: string;
  employee_id: string;
  score: number;
  proposal_rank: number;
  is_selected: boolean;
  planned_hours: number | null;
  start_date: string | null;
  end_date: string | null;
  status: string;
  explanation_text: string;
}

export interface UnassignedTaskDiagnostic {
  task_id: string;
  reason_code: "no_eligible_candidates" | "capacity_or_conflict";
  message: string;
  reason_details: string;
}

export interface PlanRunSummary {
  plan_run_id: string;
  status: string;
  created_at: string;
  planning_period_start: string | null;
  planning_period_end: string | null;
  assigned_count: number;
  unassigned_count: number;
}

export interface PlanRunArtifacts {
  eligibility: Record<string, string[]>;
  scores: Record<string, Record<string, number>>;
  solver_statistics: Record<string, number | string>;
  candidate_analysis?: Record<string, Array<Record<string, unknown>>>;
  time_estimates?: Record<string, TaskTimeEstimate>;
}

export type TimeEstimateSource = "manual" | "history" | "blended" | "rules";

export interface TaskTimeEstimate {
  source: TimeEstimateSource;
  effective_hours: number;
  manual_hours: number | null;
  rules_baseline_hours: number | null;
  historical_median_hours: number | null;
  historical_sample_size: number;
}

export interface PlanResponse {
  summary: PlanRunSummary;
  proposals: AssignmentProposal[];
  unassigned: UnassignedTaskDiagnostic[];
  artifacts: PlanRunArtifacts;
}

export interface AiSimilarCase {
  headline: string;
  source_service: string;
  source_type: string;
  source_key: string;
  outcome_note: string;
}

export interface AiExplanationPayload {
  summary: string;
  reasons: string[];
  risks: string[];
  recommended_actions: string[];
  similar_cases: AiSimilarCase[];
  advisory_note: string;
}

export interface AssignmentRationaleRequest {
  task_id: string;
  employee_id: string;
  plan_run_id: string;
}

export interface UnassignedTaskExplanationRequest {
  task_id: string;
  plan_run_id: string;
}
