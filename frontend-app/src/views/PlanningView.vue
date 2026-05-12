<script setup lang="ts">
/**
 * Owns the /planning launch and persisted review workspace, including on-demand
 * advisory explanation calls to the ai-layer for selected proposals and diagnostics.
 */
import { computed, onMounted, reactive, ref, watch } from "vue";

import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { useAuth } from "../composables/useAuth";
import { aiService } from "../services/ai-service";
import { coreService } from "../services/core-service";
import { describeRequestError } from "../services/http";
import { plannerService, planRunRequestFields, plannerResources, planningWorkflow } from "../services/planner-service";
import type {
  AiExplanationPayload,
  Assignment,
  AssignmentProposal,
  Department,
  Employee,
  PlanResponse,
  Task,
  UnassignedTaskDiagnostic,
} from "../types/api";

interface PlanningFormState {
  planning_period_start: string;
  planning_period_end: string;
  department_id: string;
}

interface ReviewFormState {
  plan_run_id: string;
}

interface ApprovalFormState {
  notes: string;
}

type AiExplanationMap = Record<string, AiExplanationPayload>;
type VisibleAiExplanationMap = Record<string, AiExplanationPayload | null>;
type AiErrorMap = Record<string, string>;
type AiLoadingMap = Record<string, boolean>;

const auth = useAuth();
const departments = ref<Department[]>([]);
const employees = ref<Employee[]>([]);
const tasks = ref<Task[]>([]);
const selectedTaskIds = ref<string[]>([]);
const latestRun = ref<PlanResponse | null>(null);
const reviewedRun = ref<PlanResponse | null>(null);
const approvedAssignment = ref<Assignment | null>(null);
const isLoading = ref(false);
const isSubmitting = ref(false);
const isReviewLoading = ref(false);
const approvingProposalKey = ref("");
const errorMessage = ref("");
const successMessage = ref("");
const reviewErrorMessage = ref("");
const reviewSuccessMessage = ref("");
const approvalErrorMessage = ref("");
const approvalSuccessMessage = ref("");
const proposalAiCache = reactive<AiExplanationMap>({});
const diagnosticAiCache = reactive<AiExplanationMap>({});
const visibleProposalAi = reactive<VisibleAiExplanationMap>({});
const visibleDiagnosticAi = reactive<VisibleAiExplanationMap>({});
const proposalAiLoadingKeys = reactive<AiLoadingMap>({});
const diagnosticAiLoadingKeys = reactive<AiLoadingMap>({});
const proposalAiErrors = reactive<AiErrorMap>({});
const diagnosticAiErrors = reactive<AiErrorMap>({});

const form = reactive<PlanningFormState>({
  planning_period_start: "",
  planning_period_end: "",
  department_id: "",
});

const reviewForm = reactive<ReviewFormState>({
  plan_run_id: "",
});

const approvalForm = reactive<ApprovalFormState>({
  notes: "",
});

const scopedTasks = computed(() => {
  if (!form.department_id) {
    return tasks.value;
  }

  return tasks.value.filter((task) => String(task.department ?? "") === form.department_id);
});

const departmentNameById = computed(() => {
  return new Map(departments.value.map((department) => [department.id, department.name]));
});

const taskTitleById = computed(() => {
  return new Map(tasks.value.map((task) => [String(task.id), task.title]));
});

const employeeNameById = computed(() => {
  return new Map(employees.value.map((employee) => [String(employee.id), employee.full_name]));
});

const canSubmit = computed(() => {
  return Boolean(auth.user.value?.id && form.planning_period_start && form.planning_period_end);
});

const selectedTaskCount = computed(() => selectedTaskIds.value.length);
const selectedProposalCount = computed(() => reviewedProposals.value.filter((proposal) => proposal.is_selected).length);

const reviewedProposals = computed(() => {
  if (!reviewedRun.value) {
    return [];
  }

  return [...reviewedRun.value.proposals].sort((left, right) => {
    if (left.is_selected !== right.is_selected) {
      return left.is_selected ? -1 : 1;
    }

    return left.proposal_rank - right.proposal_rank;
  });
});

const solverStatisticsEntries = computed(() => {
  return reviewedRun.value ? Object.entries(reviewedRun.value.artifacts.solver_statistics) : [];
});

function proposalKey(proposal: AssignmentProposal) {
  return `${proposal.task_id}-${proposal.employee_id}-${proposal.proposal_rank}`;
}

function estimateSourceLabel(source: string | undefined): string {
  if (source === "manual") {
    return "Manual estimate";
  }
  if (source === "history") {
    return "Historical estimate";
  }
  if (source === "blended") {
    return "Blended estimate";
  }
  if (source === "rules") {
    return "Rules-based estimate";
  }
  return "Estimate source unavailable";
}

function proposalTimeEstimate(proposal: AssignmentProposal) {
  if (!reviewedRun.value) {
    return null;
  }
  return reviewedRun.value.artifacts.time_estimates?.[proposal.task_id] || null;
}

/**
 * Clears every entry from a reactive record without replacing the reference.
 */
function clearReactiveRecord(record: Record<string, unknown>) {
  for (const key of Object.keys(record)) {
    delete record[key];
  }
}

/**
 * Resets only row-local AI visibility, loading, and error state for a new persisted review.
 */
function resetPlanningAiRowState() {
  clearReactiveRecord(visibleProposalAi);
  clearReactiveRecord(visibleDiagnosticAi);
  clearReactiveRecord(proposalAiLoadingKeys);
  clearReactiveRecord(diagnosticAiLoadingKeys);
  clearReactiveRecord(proposalAiErrors);
  clearReactiveRecord(diagnosticAiErrors);
}

/**
 * Builds a stable cache key for one selected proposal explanation context.
 */
function buildProposalAiKey(taskId: string, employeeId: string, planRunId: string): string {
  return `${taskId}:${employeeId}:${planRunId}`;
}

/**
 * Builds a stable cache key for one unassigned diagnostic explanation context.
 */
function buildDiagnosticAiKey(taskId: string, planRunId: string): string {
  return `${taskId}:${planRunId}`;
}

/**
 * Resolves the active AI key for one selected proposal row.
 */
function getProposalAiKey(proposal: AssignmentProposal): string | null {
  if (!reviewedRun.value) {
    return null;
  }

  return buildProposalAiKey(proposal.task_id, proposal.employee_id, reviewedRun.value.summary.plan_run_id);
}

/**
 * Returns whether one selected proposal row is currently loading an advisory explanation.
 */
function isProposalAiLoading(proposal: AssignmentProposal): boolean {
  const key = getProposalAiKey(proposal);
  return key ? Boolean(proposalAiLoadingKeys[key]) : false;
}

/**
 * Returns the row-local AI error message for one selected proposal.
 */
function getProposalAiError(proposal: AssignmentProposal): string {
  const key = getProposalAiKey(proposal);
  return key ? proposalAiErrors[key] || "" : "";
}

/**
 * Returns the currently visible advisory explanation for one selected proposal.
 */
function getVisibleProposalAi(proposal: AssignmentProposal): AiExplanationPayload | null {
  const key = getProposalAiKey(proposal);
  return key ? visibleProposalAi[key] || null : null;
}

/**
 * Loads or restores an advisory explanation for one selected persisted proposal.
 */
async function loadProposalAiExplanation(proposal: AssignmentProposal) {
  if (!reviewedRun.value || !proposal.is_selected) {
    return;
  }

  const key = getProposalAiKey(proposal);
  if (!key) {
    return;
  }

  proposalAiErrors[key] = "";

  const cachedPayload = proposalAiCache[key];
  if (cachedPayload) {
    visibleProposalAi[key] = cachedPayload;
    return;
  }

  proposalAiLoadingKeys[key] = true;
  visibleProposalAi[key] = null;

  try {
    const payload = await aiService.getAssignmentRationale({
      task_id: proposal.task_id,
      employee_id: proposal.employee_id,
      plan_run_id: reviewedRun.value.summary.plan_run_id,
    });
    proposalAiCache[key] = payload;
    visibleProposalAi[key] = payload;
  } catch (error: unknown) {
    proposalAiErrors[key] = describeRequestError(error);
  } finally {
    delete proposalAiLoadingKeys[key];
  }
}

/**
 * Resolves the active AI key for one unassigned diagnostic row.
 */
function getDiagnosticAiKey(diagnostic: UnassignedTaskDiagnostic): string | null {
  if (!reviewedRun.value) {
    return null;
  }

  return buildDiagnosticAiKey(diagnostic.task_id, reviewedRun.value.summary.plan_run_id);
}

/**
 * Returns whether one diagnostic row is currently loading an advisory explanation.
 */
function isDiagnosticAiLoading(diagnostic: UnassignedTaskDiagnostic): boolean {
  const key = getDiagnosticAiKey(diagnostic);
  return key ? Boolean(diagnosticAiLoadingKeys[key]) : false;
}

/**
 * Returns the row-local AI error message for one diagnostic.
 */
function getDiagnosticAiError(diagnostic: UnassignedTaskDiagnostic): string {
  const key = getDiagnosticAiKey(diagnostic);
  return key ? diagnosticAiErrors[key] || "" : "";
}

/**
 * Returns the currently visible advisory explanation for one diagnostic.
 */
function getVisibleDiagnosticAi(diagnostic: UnassignedTaskDiagnostic): AiExplanationPayload | null {
  const key = getDiagnosticAiKey(diagnostic);
  return key ? visibleDiagnosticAi[key] || null : null;
}

/**
 * Loads or restores an advisory explanation for one persisted unassigned diagnostic.
 */
async function loadDiagnosticAiExplanation(diagnostic: UnassignedTaskDiagnostic) {
  if (!reviewedRun.value) {
    return;
  }

  const key = getDiagnosticAiKey(diagnostic);
  if (!key) {
    return;
  }

  diagnosticAiErrors[key] = "";

  const cachedPayload = diagnosticAiCache[key];
  if (cachedPayload) {
    visibleDiagnosticAi[key] = cachedPayload;
    return;
  }

  diagnosticAiLoadingKeys[key] = true;
  visibleDiagnosticAi[key] = null;

  try {
    const payload = await aiService.getUnassignedTaskExplanation({
      task_id: diagnostic.task_id,
      plan_run_id: reviewedRun.value.summary.plan_run_id,
    });
    diagnosticAiCache[key] = payload;
    visibleDiagnosticAi[key] = payload;
  } catch (error: unknown) {
    diagnosticAiErrors[key] = describeRequestError(error);
  } finally {
    delete diagnosticAiLoadingKeys[key];
  }
}

function resetApprovalState() {
  approvingProposalKey.value = "";
  approvalErrorMessage.value = "";
  approvalSuccessMessage.value = "";
  approvedAssignment.value = null;
}

function canApproveProposal(proposal: AssignmentProposal) {
  return proposal.is_selected && Boolean(reviewedRun.value) && Number.isFinite(Number(proposal.task_id)) && Number.isFinite(Number(proposal.employee_id));
}

watch(
  () => form.department_id,
  () => {
    const visibleTaskIds = new Set(scopedTasks.value.map((task) => String(task.id)));
    selectedTaskIds.value = selectedTaskIds.value.filter((taskId) => visibleTaskIds.has(taskId));
  },
);

async function loadPlanningScope() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    const [departmentRows, employeeRows, taskRows] = await Promise.all([
      coreService.listDepartments(),
      coreService.listEmployees(),
      coreService.listTasks(),
    ]);
    departments.value = departmentRows;
    employees.value = employeeRows;
    tasks.value = taskRows;
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

async function reviewPlanRun(planRunId = reviewForm.plan_run_id.trim()) {
  if (!planRunId) {
    reviewErrorMessage.value = "Plan run ID is required to load persisted review data.";
    return;
  }

  isReviewLoading.value = true;
  reviewErrorMessage.value = "";
  reviewSuccessMessage.value = "";
  resetApprovalState();
  resetPlanningAiRowState();

  try {
    reviewedRun.value = await plannerService.getPlanRun(planRunId);
    reviewForm.plan_run_id = planRunId;
    reviewSuccessMessage.value = "Persisted plan run loaded successfully.";
  } catch (error: unknown) {
    reviewErrorMessage.value = describeRequestError(error);
  } finally {
    isReviewLoading.value = false;
  }
}

async function launchPlanRun() {
  if (!auth.user.value?.id) {
    errorMessage.value = "Authenticated manager or admin context is missing.";
    return;
  }

  isSubmitting.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    resetApprovalState();
    latestRun.value = await plannerService.createPlanRun({
      planning_period_start: form.planning_period_start,
      planning_period_end: form.planning_period_end,
      initiated_by_user_id: String(auth.user.value.id),
      department_id: form.department_id || null,
      task_ids: selectedTaskIds.value,
    });

    reviewForm.plan_run_id = latestRun.value.summary.plan_run_id;
    await reviewPlanRun(reviewForm.plan_run_id);
    successMessage.value = "Plan run launched successfully.";
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isSubmitting.value = false;
  }
}

async function approveProposal(proposal: AssignmentProposal) {
  if (!reviewedRun.value) {
    approvalErrorMessage.value = "Load a persisted plan run before approving a proposal.";
    return;
  }

  const taskId = Number(proposal.task_id);
  const employeeId = Number(proposal.employee_id);

  if (!Number.isFinite(taskId) || !Number.isFinite(employeeId)) {
    approvalErrorMessage.value = "Planner artifacts returned a proposal with non-numeric task or employee identifiers.";
    return;
  }

  approvingProposalKey.value = proposalKey(proposal);
  approvalErrorMessage.value = "";
  approvalSuccessMessage.value = "";

  try {
    approvedAssignment.value = await coreService.approveProposal({
      task: taskId,
      employee: employeeId,
      source_plan_run_id: reviewedRun.value.summary.plan_run_id,
      notes: approvalForm.notes.trim() || undefined,
    });
    approvalSuccessMessage.value = "Selected proposal was approved in core-service.";
  } catch (error: unknown) {
    approvalErrorMessage.value = describeRequestError(error);
  } finally {
    approvingProposalKey.value = "";
  }
}

onMounted(loadPlanningScope);
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Planner-service</p>
      <h3 class="page-title">Launch a persisted planning run</h3>
      <p class="page-description">
        This screen now covers plan run launch, persisted review, and the final approval handoff. Browser code still
        does not recalculate eligibility, scoring, or optimization, and `core-service` remains the authority for final
        `Assignment` creation.
      </p>
      <div class="pill-row">
        <span class="pill">/plan-runs</span>
        <span class="pill is-warm">{{ auth.user.value ? `Initiator #${auth.user.value.id}` : "No auth context" }}</span>
        <span class="pill">{{ selectedTaskCount }} selected tasks</span>
      </div>
    </section>

    <section class="page-card">
      <div class="data-layout">
        <form class="editor-card" @submit.prevent="launchPlanRun">
          <div class="editor-header">
            <div>
              <p class="section-caption">Launch planning run</p>
              <p class="resource-path">POST /api/v1/plan-runs</p>
            </div>
            <div class="inline-actions">
              <button class="button-secondary" type="button" :disabled="isLoading" @click="loadPlanningScope">
                Refresh scope
              </button>
            </div>
          </div>

          <div class="form-grid">
            <label class="field-group">
              <span class="field-label">Planning period start</span>
              <input v-model="form.planning_period_start" class="text-input" type="date" required />
            </label>

            <label class="field-group">
              <span class="field-label">Planning period end</span>
              <input v-model="form.planning_period_end" class="text-input" type="date" required />
            </label>

            <label class="field-group field-group-span-2">
              <span class="field-label">Department filter</span>
              <select v-model="form.department_id" class="select-input">
                <option value="">All departments</option>
                <option v-for="department in departments" :key="department.id" :value="String(department.id)">
                  {{ department.name }}
                </option>
              </select>
            </label>

            <div class="field-group field-group-span-2">
              <span class="field-label">Initiated by</span>
              <div class="notice">
                {{ auth.user.value ? `${auth.user.value.email} · user #${auth.user.value.id}` : "No authenticated user available" }}
              </div>
            </div>
          </div>

          <div class="action-row">
            <button class="button-primary" type="submit" :disabled="isSubmitting || !canSubmit">
              {{ isSubmitting ? "Launching..." : "Launch plan run" }}
            </button>
          </div>

          <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
          <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>
        </form>

        <div class="records-card">
          <div class="editor-header">
            <div>
              <p class="section-caption">Task scope</p>
              <p class="resource-copy">
                Leave the selection empty to let planner use all tasks inside the selected period and optional department.
              </p>
            </div>
            <span class="pill">{{ scopedTasks.length }} visible tasks</span>
          </div>

          <div v-if="isLoading" class="resource-copy">Loading tasks and departments...</div>
          <div v-else-if="scopedTasks.length === 0" class="notice">
            No tasks are currently visible for this optional department scope.
          </div>
          <ul v-else class="resource-list">
            <li v-for="task in scopedTasks" :key="task.id" class="resource-item">
              <label class="resource-heading planning-task-toggle">
                <div class="checkbox-row">
                  <input v-model="selectedTaskIds" class="check-input" type="checkbox" :value="String(task.id)" />
                  <p class="resource-label">{{ task.title }}</p>
                </div>
                <span class="pill is-warm">{{ task.priority }}</span>
              </label>
              <p class="resource-copy">
                Department:
                {{ task.department === null ? "None" : departmentNameById.get(task.department) || `#${task.department}` }}
                · Due: {{ task.due_date }}
              </p>
              <p class="resource-copy">
                Status: {{ task.status }} · Estimated: {{ task.estimated_hours === null ? "Planner estimate" : `${task.estimated_hours}h` }}
              </p>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section v-if="latestRun" class="page-card">
      <p class="eyebrow">Latest launch result</p>
      <h3 class="page-title">Plan run {{ latestRun.summary.plan_run_id }}</h3>
      <p class="page-description">
        The run was persisted in planner-service. Use the persisted review section below to re-read the same run through
        `GET /api/v1/plan-runs/{plan_run_id}`.
      </p>
      <div class="grid-two">
        <div class="records-card">
          <p class="section-caption">Summary</p>
          <ul class="key-value-list">
            <li class="key-value-item">
              <span class="key-label">Status</span>
              <span class="key-value">{{ latestRun.summary.status }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Planning period</span>
              <span class="key-value">
                {{ latestRun.summary.planning_period_start || "n/a" }} → {{ latestRun.summary.planning_period_end || "n/a" }}
              </span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Assigned count</span>
              <span class="key-value">{{ latestRun.summary.assigned_count }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Unassigned count</span>
              <span class="key-value">{{ latestRun.summary.unassigned_count }}</span>
            </li>
          </ul>
        </div>

        <div class="records-card">
          <p class="section-caption">Artifacts preview</p>
          <ul class="key-value-list">
            <li class="key-value-item">
              <span class="key-label">Proposals returned on launch</span>
              <span class="key-value">{{ latestRun.proposals.length }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Diagnostics returned on launch</span>
              <span class="key-value">{{ latestRun.unassigned.length }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Solver stats keys</span>
              <span class="key-value">{{ Object.keys(latestRun.artifacts.solver_statistics).length }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section class="page-card">
      <div class="data-layout">
        <form class="editor-card" @submit.prevent="reviewPlanRun()">
          <div class="editor-header">
            <div>
              <p class="section-caption">Review persisted plan run</p>
              <p class="resource-path">GET /api/v1/plan-runs/{plan_run_id}</p>
            </div>
            <div class="inline-actions">
              <button
                class="button-secondary"
                type="button"
                :disabled="isReviewLoading || !reviewForm.plan_run_id"
                @click="reviewPlanRun()"
              >
                Reload run
              </button>
            </div>
          </div>

          <div class="form-grid">
            <label class="field-group field-group-span-2">
              <span class="field-label">Plan run ID</span>
              <input v-model.trim="reviewForm.plan_run_id" class="text-input" required />
            </label>
          </div>

          <div class="action-row">
            <button class="button-primary" type="submit" :disabled="isReviewLoading || !reviewForm.plan_run_id">
              {{ isReviewLoading ? "Loading..." : "Load persisted run" }}
            </button>
          </div>

          <p v-if="reviewErrorMessage" class="status-banner is-error">{{ reviewErrorMessage }}</p>
          <p v-if="reviewSuccessMessage" class="status-banner is-success">{{ reviewSuccessMessage }}</p>
        </form>

        <div class="records-card">
          <div class="editor-header">
            <div>
              <p class="section-caption">Review guide</p>
              <p class="resource-copy">
                Review stays persisted and approval remains a thin handoff. The browser sends only `task`, `employee`,
                `source_plan_run_id`, and optional notes back to `core-service`.
              </p>
            </div>
            <span class="pill">{{ reviewedRun ? "Loaded" : "Waiting for run ID" }}</span>
          </div>

          <ul class="resource-list">
            <li class="resource-item">
              <p class="resource-label">What gets loaded</p>
              <p class="resource-copy">Persisted summary, proposals, diagnostics, and solver statistics from planner-service.</p>
            </li>
            <li class="resource-item">
              <p class="resource-label">What does not happen here</p>
              <p class="resource-copy">No browser-owned timing, no planner recalculation, and no mutation of persisted planner artifacts.</p>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section v-if="reviewedRun" class="page-card">
      <p class="eyebrow">Persisted review</p>
      <h3 class="page-title">Reviewing plan run {{ reviewedRun.summary.plan_run_id }}</h3>
      <p class="page-description">
        This data is reloaded from persisted planner artifacts. Manager approval below only hands back the selected
        proposal identifiers so `core-service` can recreate the final assignment from persisted planner truth.
      </p>

      <div class="grid-two">
        <div class="records-card">
          <p class="section-caption">Summary</p>
          <ul class="key-value-list">
            <li class="key-value-item">
              <span class="key-label">Status</span>
              <span class="key-value">{{ reviewedRun.summary.status }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Created at</span>
              <span class="key-value">{{ new Date(reviewedRun.summary.created_at).toLocaleString() }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Planning period</span>
              <span class="key-value">
                {{ reviewedRun.summary.planning_period_start || "n/a" }} → {{ reviewedRun.summary.planning_period_end || "n/a" }}
              </span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Assigned / unassigned</span>
              <span class="key-value">
                {{ reviewedRun.summary.assigned_count }} / {{ reviewedRun.summary.unassigned_count }}
              </span>
            </li>
          </ul>
        </div>

        <div class="records-card">
          <p class="section-caption">Artifact counts</p>
          <ul class="key-value-list">
            <li class="key-value-item">
              <span class="key-label">Proposals</span>
              <span class="key-value">{{ reviewedRun.proposals.length }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Diagnostics</span>
              <span class="key-value">{{ reviewedRun.unassigned.length }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Eligibility rows</span>
              <span class="key-value">{{ Object.keys(reviewedRun.artifacts.eligibility).length }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Score rows</span>
              <span class="key-value">{{ Object.keys(reviewedRun.artifacts.scores).length }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <div v-if="reviewedRun" class="grid-two">
      <section class="page-card">
        <div class="editor-header">
          <div>
            <p class="section-caption">Assignment proposals</p>
            <p class="resource-copy">
              Selected proposal appears first. Only the selected proposal can be approved from this screen, and the
              browser never sends timing or scoring back as manager-owned state.
            </p>
          </div>
          <div class="pill-row">
            <span class="pill">{{ reviewedProposals.length }} proposals</span>
            <span class="pill is-warm">{{ selectedProposalCount }} selected</span>
          </div>
        </div>

        <div class="resource-item">
          <p class="resource-label">Approval handoff</p>
          <p class="resource-copy">
            `core-service` re-reads the persisted proposal by `source_plan_run_id`, validates the selected
            `task + employee` pair, and writes the final approved `Assignment`.
          </p>
          <label class="field-group">
            <span class="field-label">Approval notes</span>
            <textarea
              v-model="approvalForm.notes"
              class="text-area"
              placeholder="Optional note that will be stored on the final assignment."
            />
          </label>
        </div>

        <p v-if="approvalErrorMessage" class="status-banner is-error">{{ approvalErrorMessage }}</p>
        <p v-if="approvalSuccessMessage" class="status-banner is-success">{{ approvalSuccessMessage }}</p>

        <div v-if="approvedAssignment" class="resource-item">
          <div class="resource-heading">
            <p class="resource-label">Latest approved assignment</p>
            <span class="pill is-warm">assignment #{{ approvedAssignment.id }}</span>
          </div>
          <p class="resource-copy">
            Task: {{ taskTitleById.get(String(approvedAssignment.task)) || `Task #${approvedAssignment.task}` }}
            · Employee: {{ employeeNameById.get(String(approvedAssignment.employee)) || `Employee #${approvedAssignment.employee}` }}
          </p>
          <p class="resource-copy">
            Dates: {{ approvedAssignment.start_date }} → {{ approvedAssignment.end_date }}
            · Planned hours: {{ approvedAssignment.planned_hours }}
          </p>
          <p class="resource-copy">
            Status: {{ approvedAssignment.status }}
            · Approved at: {{ approvedAssignment.approved_at ? new Date(approvedAssignment.approved_at).toLocaleString() : "n/a" }}
          </p>
        </div>

        <p v-if="reviewedProposals.length === 0" class="empty-state">No proposals were returned for this run.</p>
        <ul v-else class="resource-list">
          <li v-for="proposal in reviewedProposals" :key="proposalKey(proposal)" class="resource-item">
            <div class="resource-heading">
              <p class="resource-label">
                {{ taskTitleById.get(proposal.task_id) || `Task #${proposal.task_id}` }}
              </p>
              <div class="pill-row">
                <span class="pill" :class="{ 'is-warm': proposal.is_selected }">
                  {{ proposal.is_selected ? "selected" : "candidate" }}
                </span>
                <span class="pill">rank {{ proposal.proposal_rank }}</span>
              </div>
            </div>
            <p class="resource-copy">
              Employee: {{ employeeNameById.get(proposal.employee_id) || `Employee #${proposal.employee_id}` }}
              · Score: {{ proposal.score }}
            </p>
            <p class="resource-copy">
              Planned hours: {{ proposal.planned_hours ?? "n/a" }}
              · Dates: {{ proposal.start_date || "n/a" }} → {{ proposal.end_date || "n/a" }}
            </p>
            <p class="resource-copy">
              Estimate source: {{ estimateSourceLabel(proposalTimeEstimate(proposal)?.source) }}
              <span v-if="proposalTimeEstimate(proposal) && proposalTimeEstimate(proposal)?.source !== 'manual'">
                · Planner used {{ proposalTimeEstimate(proposal)?.effective_hours }}h
              </span>
            </p>
            <p class="resource-copy">Status: {{ proposal.status }}</p>
            <p class="resource-copy">{{ proposal.explanation_text || "No explanation text." }}</p>
            <div v-if="proposal.is_selected" class="action-row">
              <button
                class="button-secondary"
                type="button"
                :disabled="isProposalAiLoading(proposal)"
                @click="loadProposalAiExplanation(proposal)"
              >
                {{ isProposalAiLoading(proposal) ? "Explaining..." : "Explain with AI" }}
              </button>
            </div>
            <p v-if="getProposalAiError(proposal)" class="status-banner is-error">
              {{ getProposalAiError(proposal) }}
            </p>
            <div v-if="getVisibleProposalAi(proposal)" class="section-stack">
              <div>
                <p class="section-caption">Assistant explanation</p>
                <p class="resource-copy">{{ getVisibleProposalAi(proposal)?.summary }}</p>
              </div>
              <div v-if="getVisibleProposalAi(proposal)?.reasons.length">
                <p class="section-caption">Reasons</p>
                <ul class="copy-list">
                  <li v-for="reason in getVisibleProposalAi(proposal)?.reasons" :key="reason">{{ reason }}</li>
                </ul>
              </div>
              <div v-if="getVisibleProposalAi(proposal)?.risks.length">
                <p class="section-caption">Risks</p>
                <ul class="copy-list">
                  <li v-for="risk in getVisibleProposalAi(proposal)?.risks" :key="risk">{{ risk }}</li>
                </ul>
              </div>
              <div v-if="getVisibleProposalAi(proposal)?.similar_cases.length">
                <p class="section-caption">Similar cases</p>
                <ul class="resource-list">
                  <li
                    v-for="similarCase in getVisibleProposalAi(proposal)?.similar_cases"
                    :key="`${similarCase.source_key}-${similarCase.headline}`"
                    class="resource-item"
                  >
                    <p class="resource-label">{{ similarCase.headline }}</p>
                    <p class="item-meta">
                      {{ similarCase.source_service }} · {{ similarCase.source_type }} · {{ similarCase.source_key }}
                    </p>
                    <p class="resource-copy">{{ similarCase.outcome_note }}</p>
                  </li>
                </ul>
              </div>
              <div v-if="getVisibleProposalAi(proposal)?.recommended_actions.length">
                <p class="section-caption">Recommended actions</p>
                <ul class="copy-list">
                  <li
                    v-for="action in getVisibleProposalAi(proposal)?.recommended_actions"
                    :key="action"
                  >
                    {{ action }}
                  </li>
                </ul>
              </div>
              <div class="notice">
                {{ getVisibleProposalAi(proposal)?.advisory_note }}
              </div>
            </div>
            <div class="action-row">
              <button
                v-if="canApproveProposal(proposal)"
                class="button-primary"
                type="button"
                :disabled="approvingProposalKey === proposalKey(proposal)"
                @click="approveProposal(proposal)"
              >
                {{ approvingProposalKey === proposalKey(proposal) ? "Approving..." : "Approve selected proposal" }}
              </button>
              <div v-else class="notice">
                Only the selected proposal can be approved. Candidate rows remain read-only review artifacts.
              </div>
            </div>
          </li>
        </ul>
      </section>

      <section class="page-card">
        <div class="editor-header">
          <div>
            <p class="section-caption">Diagnostics</p>
            <p class="resource-copy">
              Diagnostics stay read-only and come directly from persisted planner artifacts.
            </p>
          </div>
          <span class="pill">{{ reviewedRun.unassigned.length }} diagnostics</span>
        </div>

        <p v-if="reviewedRun.unassigned.length === 0" class="empty-state">No unassigned task diagnostics for this run.</p>
        <ul v-else class="resource-list">
          <li v-for="diagnostic in reviewedRun.unassigned" :key="`${diagnostic.task_id}-${diagnostic.reason_code}`" class="resource-item">
            <div class="resource-heading">
              <p class="resource-label">
                {{ taskTitleById.get(diagnostic.task_id) || `Task #${diagnostic.task_id}` }}
              </p>
              <span class="pill is-warm">{{ diagnostic.reason_code }}</span>
            </div>
            <p class="resource-copy">{{ diagnostic.message }}</p>
            <p class="resource-copy">{{ diagnostic.reason_details }}</p>
            <div class="action-row">
              <button
                class="button-secondary"
                type="button"
                :disabled="isDiagnosticAiLoading(diagnostic)"
                @click="loadDiagnosticAiExplanation(diagnostic)"
              >
                {{ isDiagnosticAiLoading(diagnostic) ? "Explaining..." : "Explain with AI" }}
              </button>
            </div>
            <p v-if="getDiagnosticAiError(diagnostic)" class="status-banner is-error">
              {{ getDiagnosticAiError(diagnostic) }}
            </p>
            <div v-if="getVisibleDiagnosticAi(diagnostic)" class="section-stack">
              <div>
                <p class="section-caption">Assistant explanation</p>
                <p class="resource-copy">{{ getVisibleDiagnosticAi(diagnostic)?.summary }}</p>
              </div>
              <div v-if="getVisibleDiagnosticAi(diagnostic)?.reasons.length">
                <p class="section-caption">Reasons</p>
                <ul class="copy-list">
                  <li v-for="reason in getVisibleDiagnosticAi(diagnostic)?.reasons" :key="reason">{{ reason }}</li>
                </ul>
              </div>
              <div v-if="getVisibleDiagnosticAi(diagnostic)?.risks.length">
                <p class="section-caption">Risks</p>
                <ul class="copy-list">
                  <li v-for="risk in getVisibleDiagnosticAi(diagnostic)?.risks" :key="risk">{{ risk }}</li>
                </ul>
              </div>
              <div v-if="getVisibleDiagnosticAi(diagnostic)?.similar_cases.length">
                <p class="section-caption">Similar cases</p>
                <ul class="resource-list">
                  <li
                    v-for="similarCase in getVisibleDiagnosticAi(diagnostic)?.similar_cases"
                    :key="`${similarCase.source_key}-${similarCase.headline}`"
                    class="resource-item"
                  >
                    <p class="resource-label">{{ similarCase.headline }}</p>
                    <p class="item-meta">
                      {{ similarCase.source_service }} · {{ similarCase.source_type }} · {{ similarCase.source_key }}
                    </p>
                    <p class="resource-copy">{{ similarCase.outcome_note }}</p>
                  </li>
                </ul>
              </div>
              <div v-if="getVisibleDiagnosticAi(diagnostic)?.recommended_actions.length">
                <p class="section-caption">Recommended actions</p>
                <ul class="copy-list">
                  <li
                    v-for="action in getVisibleDiagnosticAi(diagnostic)?.recommended_actions"
                    :key="action"
                  >
                    {{ action }}
                  </li>
                </ul>
              </div>
              <div class="notice">
                {{ getVisibleDiagnosticAi(diagnostic)?.advisory_note }}
              </div>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <section v-if="reviewedRun" class="page-card">
      <div class="editor-header">
        <div>
          <p class="section-caption">Solver statistics</p>
          <p class="resource-copy">This section surfaces persisted solver metadata without rebuilding any optimization logic in the browser.</p>
        </div>
        <span class="pill">{{ solverStatisticsEntries.length }} keys</span>
      </div>

      <p v-if="solverStatisticsEntries.length === 0" class="empty-state">No solver statistics were persisted for this run.</p>
      <ul v-else class="key-value-list">
        <li v-for="[key, value] in solverStatisticsEntries" :key="key" class="key-value-item">
          <span class="key-label">{{ key }}</span>
          <span class="key-value">{{ value }}</span>
        </li>
      </ul>
    </section>

    <div class="grid-two">
      <SectionPlaceholder
        eyebrow="Endpoints"
        title="Planning APIs"
        description="Points 7 to 9 now cover launch, persisted review, and manager approval handoff."
      >
        <ul class="resource-list">
          <li v-for="resource in plannerResources" :key="resource.key" class="resource-item">
            <p class="resource-label">{{ resource.label }}</p>
            <p class="resource-path">{{ resource.endpoint }}</p>
            <p class="resource-copy">{{ resource.description }}</p>
            <p class="resource-copy"><strong>Next:</strong> {{ resource.nextStep }}</p>
          </li>
        </ul>
      </SectionPlaceholder>

      <SectionPlaceholder
        eyebrow="Request contract"
        title="CreatePlanRunRequest fields"
        description="These fields mirror the shared backend contract from `packages/contracts`."
      >
        <ul class="resource-list">
          <li v-for="field in planRunRequestFields" :key="field.title" class="resource-item">
            <p class="resource-label">{{ field.title }}</p>
            <p class="resource-copy">{{ field.details }}</p>
          </li>
        </ul>
      </SectionPlaceholder>
    </div>

    <SectionPlaceholder
      eyebrow="Workflow"
      title="Frontend role in planning"
      description="The client only orchestrates manager/admin actions around persisted backend flow."
    >
      <ul class="resource-list">
        <li v-for="step in planningWorkflow" :key="step.title" class="resource-item">
          <p class="resource-label">{{ step.title }}</p>
          <p class="resource-copy">{{ step.details }}</p>
        </li>
      </ul>
    </SectionPlaceholder>
  </div>
</template>

<style scoped>
.planning-task-toggle {
  align-items: start;
}
</style>
