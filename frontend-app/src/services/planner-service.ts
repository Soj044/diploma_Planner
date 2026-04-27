import { appConfig } from "../config/env";
import type {
  CreatePlanRunRequest,
  PlanResponse,
  ResourceDescriptor,
  WorkflowStepDescriptor,
} from "../types/api";
import { createJsonClient } from "./http";

const client = createJsonClient(appConfig.plannerServiceUrl);

export const plannerResources: ResourceDescriptor[] = [
  {
    key: "create-plan-run",
    label: "Create Plan Run",
    endpoint: "/plan-runs",
    description: "Launches a persisted planner run for a selected period and optional scope filters.",
    nextStep: "Add planning form after task creation screens exist.",
  },
  {
    key: "get-plan-run",
    label: "Get Persisted Plan Run",
    endpoint: "/plan-runs/{plan_run_id}",
    description: "Returns summary, proposals, diagnostics, and solver artifacts for manager review.",
    nextStep: "Add run review screen and approval CTA in the next planning slices.",
  },
];

export const planningWorkflow: WorkflowStepDescriptor[] = [
  {
    title: "Launch",
    details: "Frontend sends CreatePlanRunRequest to planner-service without embedding business truth.",
  },
  {
    title: "Snapshot pull",
    details: "planner-service requests PlanningSnapshot from core-service over the internal boundary.",
  },
  {
    title: "Review",
    details: "Manager reads persisted proposals and diagnostics from GET /plan-runs/{plan_run_id}.",
  },
  {
    title: "Approval",
    details: "Frontend hands selected task + employee + source_plan_run_id to core-service for final Assignment creation.",
  },
];

export const planRunRequestFields: WorkflowStepDescriptor[] = [
  {
    title: "planning_period_start",
    details: "Start date of the planning window.",
  },
  {
    title: "planning_period_end",
    details: "End date of the planning window.",
  },
  {
    title: "initiated_by_user_id",
    details: "Core user ID that initiated the run.",
  },
  {
    title: "department_id",
    details: "Optional scope filter for one department.",
  },
  {
    title: "task_ids",
    details: "Optional explicit task subset for a targeted run.",
  },
];

export const plannerService = {
  createPlanRun: (payload: CreatePlanRunRequest) => client.post<PlanResponse>("/plan-runs", payload),
  getPlanRun: (planRunId: string) => client.get<PlanResponse>(`/plan-runs/${planRunId}`),
};
