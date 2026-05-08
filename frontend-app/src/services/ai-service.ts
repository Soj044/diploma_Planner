/**
 * Sends authenticated frontend advisory explanation requests to the ai-layer.
 */
import { appConfig } from "../config/env";
import type {
  AiExplanationPayload,
  AssignmentRationaleRequest,
  UnassignedTaskExplanationRequest,
} from "../types/api";
import { createJsonClient } from "./http";
import { getAccessToken, refreshAccessToken } from "./auth-service";

const client = createJsonClient(appConfig.aiServiceUrl, {
  getAccessToken,
  onUnauthorized: refreshAccessToken,
});

/**
 * Requests an advisory rationale for one selected planner proposal.
 */
function getAssignmentRationale(payload: AssignmentRationaleRequest) {
  return client.post<AiExplanationPayload>("/explanations/assignment-rationale", payload);
}

/**
 * Requests an advisory explanation for one planner unassigned diagnostic.
 */
function getUnassignedTaskExplanation(payload: UnassignedTaskExplanationRequest) {
  return client.post<AiExplanationPayload>("/explanations/unassigned-task", payload);
}

export const aiService = {
  getAssignmentRationale,
  getUnassignedTaskExplanation,
};
