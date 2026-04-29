import { appConfig } from "../config/env";
import type {
  CreatePlanRunRequest,
  PlanResponse,
  ResourceDescriptor,
  WorkflowStepDescriptor,
} from "../types/api";
import { createJsonClient } from "./http";
import { getAccessToken, refreshAccessToken } from "./auth-service";

const client = createJsonClient(appConfig.plannerServiceUrl, {
  getAccessToken,
  onUnauthorized: refreshAccessToken,
});

export const plannerResources: ResourceDescriptor[] = [
  {
    key: "create-plan-run",
    label: "Create Plan Run",
    endpoint: "/plan-runs",
    description: "Launches a persisted planner run for a selected period and optional scope filters.",
    nextStep: "Implemented in point 7: manager launch form with period and scope filters.",
  },
  {
    key: "get-plan-run",
    label: "Get Persisted Plan Run",
    endpoint: "/plan-runs/{plan_run_id}",
    description: "Returns summary, proposals, diagnostics, and solver artifacts for manager review.",
    nextStep: "Implemented in point 8: persisted review screen with proposals and diagnostics; approval CTA remains a separate slice.",
  },
];

export const planningWorkflow: WorkflowStepDescriptor[] = [
  {
    title: "Launch",
    details: "Frontend sends CreatePlanRunRequest to planner-service using the authenticated manager/admin user ID.",
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
    details: "Core user ID of the currently authenticated manager or admin.",
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
