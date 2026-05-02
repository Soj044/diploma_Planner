<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import DialogModal from "../components/DialogModal.vue";
import TaskRequirementsSection from "../components/tasks/TaskRequirementsSection.vue";
import { useAuth } from "../composables/useAuth";
import { coreService } from "../services/core-service";
import { describeRequestError } from "../services/http";
import { plannerService } from "../services/planner-service";
import { setUiFlash } from "../services/ui-flash-service";
import type { AssignmentProposal, Department, Employee, PlanResponse, Task, TaskInput } from "../types/api";

interface TaskFormState {
  department: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  estimated_hours: number;
  actual_hours: string;
  start_date: string;
  due_date: string;
}

interface ManualAssignmentFormState {
  employee: string;
  planned_hours: number;
  notes: string;
}

type AssignmentMode = "suggestion" | "manual";

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

const form = reactive<TaskFormState>({
  department: "",
  title: "",
  description: "",
  status: "planned",
  priority: "medium",
  estimated_hours: 8,
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

const assignmentReadOnlyDates = computed(() => {
  return {
    start: currentTask.value?.start_date || form.start_date || "Not set",
    end: currentTask.value?.due_date || form.due_date || "Not set",
  };
});

function buildTaskPayload(): TaskInput {
  return {
    department: form.department ? Number(form.department) : null,
    title: form.title.trim(),
    description: form.description.trim(),
    status: form.status,
    priority: form.priority,
    estimated_hours: Number(form.estimated_hours),
    actual_hours: form.actual_hours ? Number(form.actual_hours) : null,
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
  form.estimated_hours = task.estimated_hours;
  form.actual_hours = task.actual_hours === null ? "" : String(task.actual_hours);
  form.start_date = task.start_date || "";
  form.due_date = task.due_date;
}

function resetManualAssignmentForm() {
  manualAssignmentForm.employee = "";
  manualAssignmentForm.planned_hours = currentTask.value?.estimated_hours || form.estimated_hours || 1;
  manualAssignmentForm.notes = "";
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

function openManualMode(message: string) {
  assignmentMode.value = "manual";
  assignmentContextMessage.value = message;
  resetManualAssignmentForm();
  isAssignmentModalOpen.value = true;
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
      manualAssignmentForm.employee = selectedProposal.value.employee_id;
      manualAssignmentForm.planned_hours = selectedProposal.value.planned_hours || task.estimated_hours;
      manualAssignmentForm.notes = "";
      isAssignmentModalOpen.value = true;
      return;
    }

    const diagnostic = currentPlanRun.value.unassigned.find((item) => item.task_id === String(task.id));
    openManualMode(
      diagnostic?.message || "Planner did not return a selected proposal for this task. You can assign manually.",
    );
  } catch (error: unknown) {
    assignmentErrorMessage.value = describeRequestError(error);
  } finally {
    isLaunchingAssignment.value = false;
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

          <label class="field-group">
            <span class="field-label">Estimated hours</span>
            <input v-model.number="form.estimated_hours" class="text-input" min="1" type="number" required />
          </label>

          <label class="field-group">
            <span class="field-label">Actual hours</span>
            <input v-model="form.actual_hours" class="text-input" min="0" type="number" />
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
              <span class="key-value">{{ selectedProposal.planned_hours ?? currentTask?.estimated_hours ?? "n/a" }}</span>
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
          <p class="section-caption">Planner explanation</p>
          <p class="resource-copy">
            {{ selectedProposal.explanation_text || "Planner did not return extra explanation text for this proposal." }}
          </p>
          <div class="notice">
            Approval still goes through the persisted planner review handoff in `core-service`. The browser does not
            create final assignments directly from planner data.
          </div>
        </section>
      </div>

      <form v-else class="page-stack" @submit.prevent="createManualAssignment">
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
          @click="openManualMode('Planner suggestion was skipped. Complete the assignment manually.')"
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
