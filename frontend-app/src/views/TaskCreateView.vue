<script setup lang="ts">
/**
 * Owns the /tasks/new create-and-assign wizard, including on-demand advisory
 * explanation calls to the ai-layer for planner suggestions and unassigned fallbacks.
 */
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import DialogModal from "../components/DialogModal.vue";
import TaskRequirementsSection from "../components/tasks/TaskRequirementsSection.vue";
import { normalizeOptionalNumericInput, type OptionalNumericInput } from "../components/tasks/taskFormNumbers";
import { useAuth } from "../composables/useAuth";
import { aiService } from "../services/ai-service";
import { coreService } from "../services/core-service";
import { describeRequestError } from "../services/http";
import { plannerService } from "../services/planner-service";
import { setUiFlash } from "../services/ui-flash-service";
import type {
  AiExplanationPayload,
  AssignmentProposal,
  AssignmentRationaleRequest,
  Department,
  Employee,
  PlanResponse,
  Task,
  TaskInput,
  UnassignedTaskDiagnostic,
  UnassignedTaskExplanationRequest,
} from "../types/api";

interface TaskFormState {
  department: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  actual_hours: OptionalNumericInput;
  start_date: string;
  due_date: string;
}

interface ManualAssignmentFormState {
  employee: string;
  planned_hours: number;
  notes: string;
}

type AssignmentMode = "suggestion" | "manual";
type ManualReason = "planner-unassigned" | "suggestion-skipped";

interface AiExplanationState {
  isLoading: boolean;
  errorMessage: string;
  payload: AiExplanationPayload | null;
}

const statusOptions = [
  { label: "Draft", value: "draft" },
  { label: "Planned", value: "planned" },
  { label: "Assigned", value: "assigned" },
  { label: "In progress", value: "in_progress" },
  { label: "Done", value: "done" },
  { label: "Cancelled", value: "cancelled" },
] as const;

const priorityOptions = [
  { label: "Low", value: "low" },
  { label: "Medium", value: "medium" },
  { label: "High", value: "high" },
  { label: "Critical", value: "critical" },
] as const;

const auth = useAuth();
const router = useRouter();

const departments = ref<Department[]>([]);
const employees = ref<Employee[]>([]);
const currentTask = ref<Task | null>(null);
const requirementReloadToken = ref(0);
const isLoading = ref(false);
const isSavingTask = ref(false);
const isLaunchingAssignment = ref(false);
const isApprovingSuggestion = ref(false);
const isCreatingManualAssignment = ref(false);
const errorMessage = ref("");
const successMessage = ref("");
const assignmentErrorMessage = ref("");
const isAssignmentModalOpen = ref(false);
const assignmentMode = ref<AssignmentMode>("manual");
const currentPlanRun = ref<PlanResponse | null>(null);
const selectedProposal = ref<AssignmentProposal | null>(null);
const assignmentContextMessage = ref("");
const manualReason = ref<ManualReason | null>(null);
const suggestionAiState = reactive<AiExplanationState>({
  isLoading: false,
  errorMessage: "",
  payload: null,
});
const unassignedAiState = reactive<AiExplanationState>({
  isLoading: false,
  errorMessage: "",
  payload: null,
});
const suggestionAiCache = reactive<Record<string, AiExplanationPayload>>({});
const unassignedAiCache = reactive<Record<string, AiExplanationPayload>>({});

const form = reactive<TaskFormState>({
  department: "",
  title: "",
  description: "",
  status: "planned",
  priority: "medium",
  actual_hours: "",
  start_date: "",
  due_date: "",
});

const manualAssignmentForm = reactive<ManualAssignmentFormState>({
  employee: "",
  planned_hours: 8,
  notes: "",
});

const employeeOptions = computed(() => {
  return [...employees.value].sort((left, right) => left.full_name.localeCompare(right.full_name));
});

const employeeNameById = computed(() => {
  return new Map(employees.value.map((employee) => [String(employee.id), employee.full_name]));
});

const canStartAssignment = computed(() => {
  return Boolean(
    form.title.trim() &&
      form.start_date &&
      form.due_date &&
      form.status === "planned" &&
      auth.user.value?.id,
  );
});
const isDoneStatus = computed(() => form.status === "done");

const assignmentReadOnlyDates = computed(() => {
  return {
    start: currentTask.value?.start_date || form.start_date || "Not set",
    end: currentTask.value?.due_date || form.due_date || "Not set",
  };
});

const currentUnassignedDiagnostic = computed<UnassignedTaskDiagnostic | null>(() => {
  if (!currentPlanRun.value || !currentTask.value) {
    return null;
  }

  return (
    currentPlanRun.value.unassigned.find((item) => item.task_id === String(currentTask.value?.id)) || null
  );
});

const canExplainUnassigned = computed(() => {
  return (
    assignmentMode.value === "manual" &&
    manualReason.value === "planner-unassigned" &&
    Boolean(currentTask.value) &&
    Boolean(currentPlanRun.value) &&
    Boolean(currentUnassignedDiagnostic.value)
  );
});

function buildTaskPayload(): TaskInput {
  const actualHours = normalizeOptionalNumericInput(form.actual_hours);
  return {
    department: form.department ? Number(form.department) : null,
    title: form.title.trim(),
    description: form.description.trim(),
    status: form.status,
    priority: form.priority,
    estimated_hours: null,
    actual_hours: actualHours,
    start_date: form.start_date || null,
    due_date: form.due_date,
    created_by_user: auth.user.value?.id ?? 0,
  };
}

function syncFormFromTask(task: Task) {
  currentTask.value = task;
  form.department = task.department === null ? "" : String(task.department);
  form.title = task.title;
  form.description = task.description;
  form.status = task.status;
  form.priority = task.priority;
  form.actual_hours = task.actual_hours === null ? "" : String(task.actual_hours);
  form.start_date = task.start_date || "";
  form.due_date = task.due_date;
}

function resetManualAssignmentForm() {
  manualAssignmentForm.employee = "";
  manualAssignmentForm.planned_hours = 1;
  manualAssignmentForm.notes = "";
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

const selectedTaskTimeEstimate = computed(() => {
  if (!currentPlanRun.value || !currentTask.value) {
    return null;
  }
  return currentPlanRun.value.artifacts.time_estimates?.[String(currentTask.value.id)] || null;
});

/**
 * Builds a stable cache key for one task/employee/proposal explanation context.
 */
function buildSuggestionAiCacheKey(taskId: number, employeeId: string, planRunId: string): string {
  return `${taskId}:${employeeId}:${planRunId}`;
}

/**
 * Builds a stable cache key for one task/unassigned diagnostic explanation context.
 */
function buildUnassignedAiCacheKey(taskId: number, planRunId: string): string {
  return `${taskId}:${planRunId}`;
}

/**
 * Resets a visible AI explanation panel without clearing its in-memory cache.
 */
function resetAiState(state: AiExplanationState) {
  state.isLoading = false;
  state.errorMessage = "";
  state.payload = null;
}

/**
 * Replaces the visible AI state with a cached explanation payload.
 */
function hydrateAiState(state: AiExplanationState, payload: AiExplanationPayload) {
  state.isLoading = false;
  state.errorMessage = "";
  state.payload = payload;
}

/**
 * Clears only the currently visible AI panels before a new planner launch.
 */
function clearVisibleAiStates() {
  resetAiState(suggestionAiState);
  resetAiState(unassignedAiState);
}

/**
 * Builds the current suggestion explanation request when planner context is present.
 */
function getSuggestionExplanationRequest(): AssignmentRationaleRequest | null {
  if (!currentTask.value || !currentPlanRun.value || !selectedProposal.value) {
    return null;
  }

  return {
    task_id: String(currentTask.value.id),
    employee_id: selectedProposal.value.employee_id,
    plan_run_id: currentPlanRun.value.summary.plan_run_id,
  };
}

/**
 * Builds the current unassigned explanation request when manual fallback came from planner diagnostics.
 */
function getUnassignedExplanationRequest(): UnassignedTaskExplanationRequest | null {
  if (!canExplainUnassigned.value || !currentTask.value || !currentPlanRun.value) {
    return null;
  }

  return {
    task_id: String(currentTask.value.id),
    plan_run_id: currentPlanRun.value.summary.plan_run_id,
  };
}

/**
 * Restores a cached suggestion explanation for the active modal context when present.
 */
function restoreSuggestionAiStateFromCache() {
  const request = getSuggestionExplanationRequest();
  if (!request) {
    resetAiState(suggestionAiState);
    return;
  }

  const cacheKey = buildSuggestionAiCacheKey(
    Number(request.task_id),
    request.employee_id,
    request.plan_run_id,
  );
  const cachedPayload = suggestionAiCache[cacheKey];
  if (cachedPayload) {
    hydrateAiState(suggestionAiState, cachedPayload);
    return;
  }

  resetAiState(suggestionAiState);
}

/**
 * Restores a cached unassigned explanation for the active modal context when present.
 */
function restoreUnassignedAiStateFromCache() {
  const request = getUnassignedExplanationRequest();
  if (!request) {
    resetAiState(unassignedAiState);
    return;
  }

  const cacheKey = buildUnassignedAiCacheKey(Number(request.task_id), request.plan_run_id);
  const cachedPayload = unassignedAiCache[cacheKey];
  if (cachedPayload) {
    hydrateAiState(unassignedAiState, cachedPayload);
    return;
  }

  resetAiState(unassignedAiState);
}

async function loadCreateContext() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    const [departmentRows, employeeRows] = await Promise.all([
      coreService.listDepartments(),
      coreService.listEmployees(),
    ]);
    departments.value = departmentRows;
    employees.value = employeeRows;
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

async function persistTask(): Promise<Task | null> {
  if (!auth.user.value?.id) {
    errorMessage.value = "Authenticated manager/admin context is missing.";
    return null;
  }
  const actualHours = normalizeOptionalNumericInput(form.actual_hours);
  if (isDoneStatus.value && actualHours === null) {
    errorMessage.value = "Done tasks require actual_hours before saving.";
    return null;
  }
  if (!isDoneStatus.value && actualHours !== null) {
    errorMessage.value = "Actual hours are allowed only when status is done.";
    return null;
  }

  isSavingTask.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const isCreate = currentTask.value === null;
    const payload = buildTaskPayload();
    const task =
      currentTask.value === null
        ? await coreService.createTask(payload)
        : await coreService.updateTask(currentTask.value.id, payload);
    syncFormFromTask(task);
    requirementReloadToken.value += 1;
    successMessage.value = isCreate ? "Task created." : "Task updated.";
    return task;
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
    return null;
  } finally {
    isSavingTask.value = false;
  }
}

async function handleSaveTask() {
  const task = await persistTask();
  if (!task) {
    return;
  }

  setUiFlash({
    kind: "success",
    text: `Task “${task.title}” was saved.`,
  });
  await router.push({ name: "tasks" });
}

/**
 * Opens the manual assignment branch and keeps track of why the user reached it.
 */
function openManualMode(message: string, reason: ManualReason) {
  assignmentMode.value = "manual";
  assignmentContextMessage.value = message;
  manualReason.value = reason;
  resetManualAssignmentForm();
  isAssignmentModalOpen.value = true;
  restoreUnassignedAiStateFromCache();
}

async function handleSaveAndAssign() {
  const task = await persistTask();
  if (!task) {
    return;
  }

  if (!task.start_date || task.status !== "planned") {
    errorMessage.value = "Save + Assignment requires a planned task with both start_date and due_date.";
    return;
  }

  isLaunchingAssignment.value = true;
  assignmentErrorMessage.value = "";
  clearVisibleAiStates();

  try {
    const launchedRun = await plannerService.createPlanRun({
      planning_period_start: task.start_date,
      planning_period_end: task.due_date,
      initiated_by_user_id: String(auth.user.value?.id ?? ""),
      task_ids: [String(task.id)],
    });

    currentPlanRun.value = await plannerService.getPlanRun(launchedRun.summary.plan_run_id);
    selectedProposal.value =
      currentPlanRun.value.proposals.find(
        (proposal) => proposal.task_id === String(task.id) && proposal.is_selected,
      ) || null;

    if (selectedProposal.value) {
      assignmentMode.value = "suggestion";
      assignmentContextMessage.value = "Planner selected one candidate for this task.";
      manualReason.value = null;
      manualAssignmentForm.employee = selectedProposal.value.employee_id;
      manualAssignmentForm.planned_hours = selectedProposal.value.planned_hours || 1;
      manualAssignmentForm.notes = "";
      isAssignmentModalOpen.value = true;
      restoreSuggestionAiStateFromCache();
      return;
    }

    const diagnostic = currentPlanRun.value.unassigned.find((item) => item.task_id === String(task.id));
    openManualMode(
      diagnostic?.message || "Planner did not return a selected proposal for this task. You can assign manually.",
      "planner-unassigned",
    );
  } catch (error: unknown) {
    assignmentErrorMessage.value = describeRequestError(error);
  } finally {
    isLaunchingAssignment.value = false;
  }
}

/**
 * Loads an on-demand AI explanation for the currently selected planner proposal.
 */
async function loadSuggestionAiExplanation() {
  const request = getSuggestionExplanationRequest();
  if (!request) {
    suggestionAiState.errorMessage = "Planner suggestion context is missing.";
    suggestionAiState.payload = null;
    return;
  }

  const cacheKey = buildSuggestionAiCacheKey(
    Number(request.task_id),
    request.employee_id,
    request.plan_run_id,
  );
  const cachedPayload = suggestionAiCache[cacheKey];
  if (cachedPayload) {
    hydrateAiState(suggestionAiState, cachedPayload);
    return;
  }

  suggestionAiState.isLoading = true;
  suggestionAiState.errorMessage = "";
  suggestionAiState.payload = null;

  try {
    const payload = await aiService.getAssignmentRationale(request);
    suggestionAiCache[cacheKey] = payload;
    hydrateAiState(suggestionAiState, payload);
  } catch (error: unknown) {
    suggestionAiState.errorMessage = describeRequestError(error);
  } finally {
    suggestionAiState.isLoading = false;
  }
}

/**
 * Loads an on-demand AI explanation for planner-driven manual fallback.
 */
async function loadUnassignedAiExplanation() {
  const request = getUnassignedExplanationRequest();
  if (!request) {
    unassignedAiState.errorMessage = "Planner diagnostic context is missing.";
    unassignedAiState.payload = null;
    return;
  }

  const cacheKey = buildUnassignedAiCacheKey(Number(request.task_id), request.plan_run_id);
  const cachedPayload = unassignedAiCache[cacheKey];
  if (cachedPayload) {
    hydrateAiState(unassignedAiState, cachedPayload);
    return;
  }

  unassignedAiState.isLoading = true;
  unassignedAiState.errorMessage = "";
  unassignedAiState.payload = null;

  try {
    const payload = await aiService.getUnassignedTaskExplanation(request);
    unassignedAiCache[cacheKey] = payload;
    hydrateAiState(unassignedAiState, payload);
  } catch (error: unknown) {
    unassignedAiState.errorMessage = describeRequestError(error);
  } finally {
    unassignedAiState.isLoading = false;
  }
}

async function approveSuggestion() {
  if (!currentTask.value || !currentPlanRun.value || !selectedProposal.value) {
    assignmentErrorMessage.value = "Planner suggestion context is missing.";
    return;
  }

  isApprovingSuggestion.value = true;
  assignmentErrorMessage.value = "";

  try {
    await coreService.approveProposal({
      task: currentTask.value.id,
      employee: Number(selectedProposal.value.employee_id),
      source_plan_run_id: currentPlanRun.value.summary.plan_run_id,
    });
    setUiFlash({
      kind: "success",
      text: `Task “${currentTask.value.title}” was assigned from the planner suggestion.`,
    });
    isAssignmentModalOpen.value = false;
    await router.push({ name: "tasks" });
  } catch (error: unknown) {
    assignmentErrorMessage.value = describeRequestError(error);
  } finally {
    isApprovingSuggestion.value = false;
  }
}

async function createManualAssignment() {
  if (!currentTask.value) {
    assignmentErrorMessage.value = "Task context is missing.";
    return;
  }

  if (!manualAssignmentForm.employee) {
    assignmentErrorMessage.value = "Choose an employee before creating a manual assignment.";
    return;
  }

  isCreatingManualAssignment.value = true;
  assignmentErrorMessage.value = "";

  try {
    await coreService.createManualAssignment({
      task: currentTask.value.id,
      employee: Number(manualAssignmentForm.employee),
      planned_hours: Number(manualAssignmentForm.planned_hours),
      notes: manualAssignmentForm.notes.trim() || undefined,
    });
    setUiFlash({
      kind: "success",
      text: `Task “${currentTask.value.title}” was assigned manually.`,
    });
    isAssignmentModalOpen.value = false;
    await router.push({ name: "tasks" });
  } catch (error: unknown) {
    assignmentErrorMessage.value = describeRequestError(error);
  } finally {
    isCreatingManualAssignment.value = false;
  }
}

onMounted(loadCreateContext);
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Task creation</p>
      <h3 class="page-title">Create a planned task and continue into assignment</h3>
      <p class="page-description">
        This flow keeps task creation in `core-service`, adds task requirements on the same page, and reuses the
        existing persisted planner boundary for single-task assignment.
      </p>
      <div class="pill-row">
        <span class="pill">/tasks/new</span>
        <span class="pill">POST /api/v1/tasks/</span>
        <span class="pill is-warm">
          {{ currentTask ? `Task #${currentTask.id}` : "Unsaved task" }}
        </span>
      </div>
    </section>

    <section class="page-card">
      <div class="editor-header">
        <div>
          <p class="section-caption">Task details</p>
          <p class="resource-copy">
            Save the task first. The assignment flow is enabled only for a saved task with `status=planned`,
            `start_date`, and `due_date`.
          </p>
        </div>
      </div>

      <div v-if="isLoading" class="resource-copy">Loading departments and employees...</div>
      <form v-else @submit.prevent>
        <div class="form-grid">
          <label class="field-group">
            <span class="field-label">Title</span>
            <input v-model.trim="form.title" class="text-input" required />
          </label>

          <label class="field-group">
            <span class="field-label">Department</span>
            <select v-model="form.department" class="select-input">
              <option value="">No department</option>
              <option v-for="department in departments" :key="department.id" :value="String(department.id)">
                {{ department.name }}
              </option>
            </select>
          </label>

          <label class="field-group field-group-span-2">
            <span class="field-label">Description</span>
            <textarea v-model.trim="form.description" class="text-area" rows="4" />
          </label>

          <label class="field-group">
            <span class="field-label">Status</span>
            <select v-model="form.status" class="select-input">
              <option v-for="option in statusOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <label class="field-group">
            <span class="field-label">Priority</span>
            <select v-model="form.priority" class="select-input">
              <option v-for="option in priorityOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <label v-if="isDoneStatus" class="field-group">
            <span class="field-label">Actual hours</span>
            <input v-model="form.actual_hours" class="text-input" min="1" type="number" required />
          </label>

          <label class="field-group">
            <span class="field-label">Start date</span>
            <input v-model="form.start_date" class="text-input" type="date" />
          </label>

          <label class="field-group">
            <span class="field-label">Due date</span>
            <input v-model="form.due_date" class="text-input" type="date" required />
          </label>
        </div>

        <div class="notice">
          Save + Assignment is available only when the task is already saved and stays in `planned` status with both
          planning dates filled in.
        </div>

        <div class="action-row">
          <button class="button-secondary" type="button" :disabled="isSavingTask" @click="handleSaveTask">
            {{ isSavingTask ? "Saving..." : "Save task" }}
          </button>
          <button
            class="button-primary"
            type="button"
            :disabled="isSavingTask || isLaunchingAssignment || !canStartAssignment"
            @click="handleSaveAndAssign"
          >
            {{ isLaunchingAssignment ? "Launching assignment..." : "Save + Assignment" }}
          </button>
        </div>

        <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
        <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>
      </form>
    </section>

    <section v-if="currentTask" class="page-card">
      <div class="editor-header">
        <div>
          <p class="section-caption">Task requirements</p>
          <p class="resource-copy">Requirements attach to the saved task on the same route before assignment.</p>
        </div>
        <span class="pill">Task #{{ currentTask.id }}</span>
      </div>

      <TaskRequirementsSection :selected-task-id="currentTask.id" :reload-token="requirementReloadToken" />
    </section>

    <DialogModal
      :open="isAssignmentModalOpen"
      :wide="true"
      :title="assignmentMode === 'suggestion' ? 'Planner suggestion' : 'Manual assignment'"
      :description="assignmentContextMessage"
      @close="isAssignmentModalOpen = false"
    >
      <p v-if="assignmentErrorMessage" class="status-banner is-error">{{ assignmentErrorMessage }}</p>

      <div v-if="assignmentMode === 'suggestion' && selectedProposal" class="grid-two">
        <section class="records-card">
          <p class="section-caption">Suggested assignee</p>
          <ul class="key-value-list">
            <li class="key-value-item">
              <span class="key-label">Employee</span>
              <span class="key-value">
                {{ employeeNameById.get(selectedProposal.employee_id) || `Employee #${selectedProposal.employee_id}` }}
              </span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Planned hours</span>
              <span class="key-value">{{ selectedProposal.planned_hours ?? "n/a" }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Estimate source</span>
              <span class="key-value">{{ estimateSourceLabel(selectedTaskTimeEstimate?.source) }}</span>
            </li>
            <li
              v-if="selectedTaskTimeEstimate && selectedTaskTimeEstimate.source !== 'manual'"
              class="key-value-item"
            >
              <span class="key-label">Planner used hours</span>
              <span class="key-value">{{ selectedTaskTimeEstimate.effective_hours }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Start date</span>
              <span class="key-value">{{ selectedProposal.start_date || assignmentReadOnlyDates.start }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">End date</span>
              <span class="key-value">{{ selectedProposal.end_date || assignmentReadOnlyDates.end }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Score</span>
              <span class="key-value">{{ selectedProposal.score }}</span>
            </li>
          </ul>
        </section>

        <section class="records-card">
          <div class="editor-header">
            <div>
              <p class="section-caption">Planner explanation</p>
              <p class="resource-copy">
                {{ selectedProposal.explanation_text || "Planner did not return extra explanation text for this proposal." }}
              </p>
            </div>
            <button
              class="button-secondary"
              type="button"
              :disabled="suggestionAiState.isLoading"
              @click="loadSuggestionAiExplanation"
            >
              {{ suggestionAiState.isLoading ? "Explaining..." : "Explain with AI" }}
            </button>
          </div>

          <p v-if="suggestionAiState.errorMessage" class="status-banner is-error">
            {{ suggestionAiState.errorMessage }}
          </p>
          <div v-else-if="suggestionAiState.payload" class="section-stack">
            <div>
              <p class="section-caption">AI summary</p>
              <p class="resource-copy">{{ suggestionAiState.payload.summary }}</p>
            </div>
            <div v-if="suggestionAiState.payload.reasons.length">
              <p class="section-caption">Reasons</p>
              <ul class="copy-list">
                <li v-for="reason in suggestionAiState.payload.reasons" :key="reason">{{ reason }}</li>
              </ul>
            </div>
            <div v-if="suggestionAiState.payload.risks.length">
              <p class="section-caption">Risks</p>
              <ul class="copy-list">
                <li v-for="risk in suggestionAiState.payload.risks" :key="risk">{{ risk }}</li>
              </ul>
            </div>
            <div v-if="suggestionAiState.payload.similar_cases.length">
              <p class="section-caption">Similar cases</p>
              <ul class="resource-list">
                <li
                  v-for="similarCase in suggestionAiState.payload.similar_cases"
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
            <div v-if="suggestionAiState.payload.recommended_actions.length">
              <p class="section-caption">Recommended actions</p>
              <ul class="copy-list">
                <li v-for="action in suggestionAiState.payload.recommended_actions" :key="action">{{ action }}</li>
              </ul>
            </div>
            <div class="notice">
              {{ suggestionAiState.payload.advisory_note }}
            </div>
          </div>
          <p v-else-if="suggestionAiState.isLoading" class="resource-copy">Loading AI explanation...</p>

          <div class="notice">
            Approval still goes through the persisted planner review handoff in `core-service`. The browser does not
            create final assignments directly from planner data.
          </div>
        </section>
      </div>

      <form v-else class="page-stack" @submit.prevent="createManualAssignment">
        <section v-if="canExplainUnassigned" class="records-card">
          <div class="editor-header">
            <div>
              <p class="section-caption">AI fallback explanation</p>
              <p class="resource-copy">
                Request an advisory explanation for why the planner did not return a selected assignee.
              </p>
            </div>
            <button
              class="button-secondary"
              type="button"
              :disabled="unassignedAiState.isLoading"
              @click="loadUnassignedAiExplanation"
            >
              {{ unassignedAiState.isLoading ? "Explaining..." : "Explain why no assignee" }}
            </button>
          </div>

          <p v-if="unassignedAiState.errorMessage" class="status-banner is-error">
            {{ unassignedAiState.errorMessage }}
          </p>
          <div v-else-if="unassignedAiState.payload" class="section-stack">
            <div>
              <p class="section-caption">AI summary</p>
              <p class="resource-copy">{{ unassignedAiState.payload.summary }}</p>
            </div>
            <div v-if="unassignedAiState.payload.reasons.length">
              <p class="section-caption">Reasons</p>
              <ul class="copy-list">
                <li v-for="reason in unassignedAiState.payload.reasons" :key="reason">{{ reason }}</li>
              </ul>
            </div>
            <div v-if="unassignedAiState.payload.risks.length">
              <p class="section-caption">Risks</p>
              <ul class="copy-list">
                <li v-for="risk in unassignedAiState.payload.risks" :key="risk">{{ risk }}</li>
              </ul>
            </div>
            <div v-if="unassignedAiState.payload.similar_cases.length">
              <p class="section-caption">Similar cases</p>
              <ul class="resource-list">
                <li
                  v-for="similarCase in unassignedAiState.payload.similar_cases"
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
            <div v-if="unassignedAiState.payload.recommended_actions.length">
              <p class="section-caption">Recommended actions</p>
              <ul class="copy-list">
                <li v-for="action in unassignedAiState.payload.recommended_actions" :key="action">{{ action }}</li>
              </ul>
            </div>
            <div class="notice">
              {{ unassignedAiState.payload.advisory_note }}
            </div>
          </div>
          <p v-else-if="unassignedAiState.isLoading" class="resource-copy">Loading AI explanation...</p>
        </section>

        <section class="records-card">
          <p class="section-caption">Assignment window</p>
          <ul class="key-value-list">
            <li class="key-value-item">
              <span class="key-label">Start date</span>
              <span class="key-value">{{ assignmentReadOnlyDates.start }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">End date</span>
              <span class="key-value">{{ assignmentReadOnlyDates.end }}</span>
            </li>
          </ul>
        </section>

        <section class="records-card">
          <div class="form-grid">
            <label class="field-group">
              <span class="field-label">Employee</span>
              <select v-model="manualAssignmentForm.employee" class="select-input" required>
                <option value="">Choose employee</option>
                <option v-for="employee in employeeOptions" :key="employee.id" :value="String(employee.id)">
                  {{ employee.full_name }}
                </option>
              </select>
            </label>

            <label class="field-group">
              <span class="field-label">Planned hours</span>
              <input
                v-model.number="manualAssignmentForm.planned_hours"
                class="text-input"
                min="1"
                type="number"
                required
              />
            </label>

            <label class="field-group field-group-span-2">
              <span class="field-label">Notes</span>
              <textarea v-model.trim="manualAssignmentForm.notes" class="text-area" rows="4" />
            </label>
          </div>
        </section>
      </form>

      <template #actions>
        <button
          v-if="assignmentMode === 'suggestion' && selectedProposal"
          class="button-secondary"
          type="button"
          @click="openManualMode('Planner suggestion was skipped. Complete the assignment manually.', 'suggestion-skipped')"
        >
          Use manual assignment
        </button>
        <button
          v-if="assignmentMode === 'suggestion' && selectedProposal"
          class="button-primary"
          type="button"
          :disabled="isApprovingSuggestion"
          @click="approveSuggestion"
        >
          {{ isApprovingSuggestion ? "Approving..." : "Approve suggestion" }}
        </button>
        <button
          v-else
          class="button-primary"
          type="button"
          :disabled="isCreatingManualAssignment"
          @click="createManualAssignment"
        >
          {{ isCreatingManualAssignment ? "Creating..." : "Create assignment" }}
        </button>
      </template>
    </DialogModal>
  </div>
</template>
