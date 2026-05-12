<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import SectionPlaceholder from "../SectionPlaceholder.vue";
import { useAuth } from "../../composables/useAuth";
import { coreService } from "../../services/core-service";
import { describeRequestError } from "../../services/http";
import type { Department, Task, TaskInput } from "../../types/api";
import { normalizeOptionalNumericInput, type OptionalNumericInput } from "./taskFormNumbers";

const emit = defineEmits<{
  "selected-task-change": [taskId: number | null];
  "tasks-updated": [];
}>();

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
const tasks = ref<Task[]>([]);
const departments = ref<Department[]>([]);
const selectedTaskId = ref<number | null>(null);
const isLoading = ref(false);
const isSaving = ref(false);
const deletingId = ref<number | null>(null);
const editingId = ref<number | null>(null);
const creatorUserId = ref<number | null>(null);
const errorMessage = ref("");
const successMessage = ref("");

const form = reactive<TaskFormState>({
  department: "",
  title: "",
  description: "",
  status: "draft",
  priority: "medium",
  actual_hours: "",
  start_date: "",
  due_date: "",
});

const departmentNameById = computed(() => {
  return new Map(departments.value.map((department) => [department.id, department.name]));
});

const canManageTasks = computed(() => {
  return auth.role.value === "admin" || auth.role.value === "manager";
});
const isDoneStatus = computed(() => form.status === "done");

const creatorLabel = computed(() => {
  if (creatorUserId.value === null) {
    return "No creator selected";
  }

  if (creatorUserId.value === auth.user.value?.id) {
    return `Current session user · ${auth.user.value.email}`;
  }

  return `Preserved creator #${creatorUserId.value}`;
});

function resetForm() {
  form.department = "";
  form.title = "";
  form.description = "";
  form.status = "draft";
  form.priority = "medium";
  form.actual_hours = "";
  form.start_date = "";
  form.due_date = "";
  creatorUserId.value = auth.user.value?.id ?? null;
  editingId.value = null;
}

function setSelectedTask(taskId: number | null) {
  selectedTaskId.value = taskId;
  emit("selected-task-change", taskId);
}

function startEditing(task: Task) {
  if (!canManageTasks.value) {
    return;
  }

  editingId.value = task.id;
  form.department = task.department === null ? "" : String(task.department);
  form.title = task.title;
  form.description = task.description;
  form.status = task.status;
  form.priority = task.priority;
  form.actual_hours = task.actual_hours === null ? "" : String(task.actual_hours);
  form.start_date = task.start_date || "";
  form.due_date = task.due_date;
  creatorUserId.value = task.created_by_user;
  setSelectedTask(task.id);
  errorMessage.value = "";
  successMessage.value = "";
}

async function load() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    const [taskRows, departmentRows] = await Promise.all([
      coreService.listTasks(),
      coreService.listDepartments(),
    ]);
    tasks.value = taskRows;
    departments.value = departmentRows;

    if (selectedTaskId.value !== null && !tasks.value.some((task) => task.id === selectedTaskId.value)) {
      setSelectedTask(null);
    }
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

function buildPayload(): TaskInput {
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
    created_by_user: creatorUserId.value ?? auth.user.value?.id ?? 0,
  };
}

async function save() {
  if (!canManageTasks.value) {
    return;
  }

  if (auth.user.value?.id === undefined) {
    errorMessage.value = "Current authenticated user context is missing.";
    return;
  }
  const actualHours = normalizeOptionalNumericInput(form.actual_hours);
  if (isDoneStatus.value && actualHours === null) {
    errorMessage.value = "Done tasks require actual_hours before saving.";
    return;
  }
  if (!isDoneStatus.value && actualHours !== null) {
    errorMessage.value = "Actual hours are allowed only when status is done.";
    return;
  }

  isSaving.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const payload = buildPayload();
    const savedTask =
      editingId.value === null
        ? await coreService.createTask(payload)
        : await coreService.updateTask(editingId.value, payload);

    successMessage.value = editingId.value === null ? "Task created." : "Task updated.";
    resetForm();
    setSelectedTask(savedTask.id);
    await load();
    emit("tasks-updated");
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isSaving.value = false;
  }
}

async function remove(id: number) {
  if (!canManageTasks.value) {
    return;
  }

  deletingId.value = id;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    await coreService.deleteTask(id);
    successMessage.value = "Task deleted.";
    if (editingId.value === id) {
      resetForm();
    }
    if (selectedTaskId.value === id) {
      setSelectedTask(null);
    }
    await load();
    emit("tasks-updated");
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    deletingId.value = null;
  }
}

onMounted(async () => {
  await load();
  resetForm();
});
</script>

<template>
  <SectionPlaceholder
    eyebrow="Tasks"
    title="Task creation stays inside core-service truth"
    description="Managers can create and maintain planner-visible tasks directly in the frontend shell, while employees stay in read-only mode."
  >
    <div class="data-layout" :class="{ 'data-layout-single': !canManageTasks }">
      <form v-if="canManageTasks" class="editor-card" @submit.prevent="save">
        <div class="editor-header">
          <div>
            <p class="section-caption">{{ editingId === null ? "Create task" : "Edit task" }}</p>
            <p class="resource-path">/tasks/</p>
          </div>
          <div class="inline-actions">
            <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
            <button
              v-if="editingId !== null"
              class="button-secondary"
              type="button"
              :disabled="isSaving"
              @click="resetForm"
            >
              Cancel edit
            </button>
          </div>
        </div>

        <div class="form-grid">
          <label class="field-group">
            <span class="field-label">Title</span>
            <input v-model.trim="form.title" class="text-input" required />
          </label>

          <label class="field-group">
            <span class="field-label">Department</span>
            <select v-model="form.department" class="select-input">
              <option value="">No department</option>
              <option
                v-for="department in departments"
                :key="department.id"
                :value="String(department.id)"
              >
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

          <div class="field-group field-group-span-2">
            <span class="field-label">Created by user</span>
            <div class="notice">{{ creatorLabel }}</div>
          </div>
        </div>

        <div class="action-row">
          <button class="button-primary" type="submit" :disabled="isSaving">
            {{ isSaving ? "Saving..." : editingId === null ? "Create task" : "Save task" }}
          </button>
        </div>

        <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
        <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>
      </form>

      <div class="records-card">
        <div class="editor-header">
          <div>
            <p class="section-caption">Existing tasks</p>
            <p class="resource-copy">Use “Requirements” to focus the skill requirement editor on one task.</p>
          </div>
          <span class="pill">{{ tasks.length }} rows</span>
        </div>

        <div v-if="!canManageTasks" class="notice">
          Employee access to tasks is intentionally read-only. Task creation and edits remain manager/admin actions.
        </div>

        <p v-if="isLoading" class="resource-copy">Loading...</p>
        <p v-else-if="tasks.length === 0" class="empty-state">No tasks yet.</p>
        <ul v-else class="resource-list">
          <li
            v-for="task in tasks"
            :key="task.id"
            class="resource-item"
            :class="{ 'resource-item-active': selectedTaskId === task.id }"
          >
            <div class="resource-heading">
              <p class="resource-label">{{ task.title }}</p>
              <div class="inline-actions">
                <button class="button-secondary" type="button" @click="setSelectedTask(task.id)">Requirements</button>
                <button v-if="canManageTasks" class="button-secondary" type="button" @click="startEditing(task)">Edit</button>
                <button
                  v-if="canManageTasks"
                  class="button-danger"
                  type="button"
                  :disabled="deletingId === task.id"
                  @click="remove(task.id)"
                >
                  {{ deletingId === task.id ? "Deleting..." : "Delete" }}
                </button>
              </div>
            </div>
            <div class="pill-row">
              <span class="pill">{{ task.status }}</span>
              <span class="pill is-warm">{{ task.priority }}</span>
            </div>
            <p class="resource-copy">
              Department:
              {{ task.department === null ? "None" : departmentNameById.get(task.department) || `#${task.department}` }}
              · Created by:
              {{ task.created_by_user === auth.user.value?.id ? "You" : `User #${task.created_by_user}` }}
            </p>
            <p class="resource-copy">
              Estimated: {{ task.estimated_hours === null ? "Planner estimate" : `${task.estimated_hours}h` }}
              <span v-if="task.actual_hours !== null"> · Actual: {{ task.actual_hours }}h</span>
              · Due: {{ task.due_date }}
            </p>
            <p class="item-meta">ID {{ task.id }} · updated {{ new Date(task.updated_at).toLocaleString() }}</p>
          </li>
        </ul>
      </div>
    </div>
  </SectionPlaceholder>
</template>
