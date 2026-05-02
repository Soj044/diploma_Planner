<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import { useAuth } from "../../composables/useAuth";
import { coreService } from "../../services/core-service";
import { describeRequestError } from "../../services/http";
import { consumeUiFlash } from "../../services/ui-flash-service";
import type { Department, Task, TaskInput } from "../../types/api";

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
  estimated_hours: number;
  actual_hours: string;
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
const editingId = ref<number | null>(null);
const isLoading = ref(false);
const isSaving = ref(false);
const deletingId = ref<number | null>(null);
const errorMessage = ref("");
const successMessage = ref("");

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

const departmentNameById = computed(() => {
  return new Map(departments.value.map((department) => [department.id, department.name]));
});

const canDeleteTasks = computed(() => auth.role.value === "admin");

const visibleTasks = computed(() => {
  const currentUserId = auth.user.value?.id;
  return [...tasks.value]
    .filter((task) => task.created_by_user === currentUserId)
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at));
});

function setSelectedTask(taskId: number | null) {
  selectedTaskId.value = taskId;
  emit("selected-task-change", taskId);
}

function resetForm() {
  editingId.value = null;
  form.department = "";
  form.title = "";
  form.description = "";
  form.status = "planned";
  form.priority = "medium";
  form.estimated_hours = 8;
  form.actual_hours = "";
  form.start_date = "";
  form.due_date = "";
}

function startEditing(task: Task) {
  editingId.value = task.id;
  form.department = task.department === null ? "" : String(task.department);
  form.title = task.title;
  form.description = task.description;
  form.status = task.status;
  form.priority = task.priority;
  form.estimated_hours = task.estimated_hours;
  form.actual_hours = task.actual_hours === null ? "" : String(task.actual_hours);
  form.start_date = task.start_date || "";
  form.due_date = task.due_date;
  setSelectedTask(task.id);
  errorMessage.value = "";
  successMessage.value = "";
}

function buildPayload(): TaskInput {
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

    if (selectedTaskId.value !== null && !visibleTasks.value.some((task) => task.id === selectedTaskId.value)) {
      setSelectedTask(null);
    }

    const flash = consumeUiFlash();
    if (flash) {
      if (flash.kind === "success") {
        successMessage.value = flash.text;
      } else {
        errorMessage.value = flash.text;
      }
    }
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

async function save() {
  if (editingId.value === null) {
    return;
  }

  isSaving.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const updatedTask = await coreService.updateTask(editingId.value, buildPayload());
    successMessage.value = "Task updated.";
    setSelectedTask(updatedTask.id);
    await load();
    emit("tasks-updated");
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isSaving.value = false;
  }
}

async function remove(taskId: number) {
  deletingId.value = taskId;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    await coreService.deleteTask(taskId);
    successMessage.value = "Task deleted.";
    if (editingId.value === taskId) {
      resetForm();
    }
    if (selectedTaskId.value === taskId) {
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
});
</script>

<template>
  <section class="page-card">
    <div class="editor-header">
      <div>
        <p class="section-caption">My task workspace</p>
        <p class="resource-copy">
          This list is scoped to tasks created by the current manager/admin session. New task creation moved into a
          dedicated create-and-assign flow.
        </p>
      </div>
      <div class="inline-actions">
        <RouterLink class="button-primary" to="/tasks/new">Create task</RouterLink>
        <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
      </div>
    </div>

    <div class="data-layout">
      <section class="records-card">
        <div class="editor-header">
          <div>
            <p class="section-caption">Existing tasks</p>
            <p class="resource-copy">Use Requirements to focus the existing task requirement editor below.</p>
          </div>
          <span class="pill">{{ visibleTasks.length }} rows</span>
        </div>

        <p v-if="isLoading" class="resource-copy">Loading tasks...</p>
        <p v-else-if="visibleTasks.length === 0" class="empty-state">No tasks created by this user yet.</p>
        <ul v-else class="resource-list">
          <li
            v-for="task in visibleTasks"
            :key="task.id"
            class="resource-item"
            :class="{ 'resource-item-active': selectedTaskId === task.id }"
          >
            <div class="resource-heading">
              <p class="resource-label">{{ task.title }}</p>
              <div class="inline-actions">
                <button class="button-secondary" type="button" @click="setSelectedTask(task.id)">Requirements</button>
                <button class="button-secondary" type="button" @click="startEditing(task)">Edit</button>
                <button
                  v-if="canDeleteTasks"
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
            </p>
            <p class="resource-copy">
              Estimated: {{ task.estimated_hours }}h
              <span v-if="task.actual_hours !== null">· Actual: {{ task.actual_hours }}h</span>
              · Start: {{ task.start_date || "Not set" }}
              · Due: {{ task.due_date }}
            </p>
            <p class="item-meta">ID {{ task.id }} · updated {{ new Date(task.updated_at).toLocaleString() }}</p>
          </li>
        </ul>
      </section>

      <section class="editor-card">
        <div class="editor-header">
          <div>
            <p class="section-caption">{{ editingId === null ? "Edit task" : `Editing task #${editingId}` }}</p>
            <p class="resource-path">PATCH /tasks/{id}/</p>
          </div>
          <div class="inline-actions">
            <button v-if="editingId !== null" class="button-secondary" type="button" :disabled="isSaving" @click="resetForm">
              Cancel edit
            </button>
          </div>
        </div>

        <div v-if="editingId === null" class="notice">
          Select an existing task to edit it here, or start a new create-and-assignment flow from the “Create task”
          button.
        </div>

        <form v-else @submit.prevent="save">
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

          <div class="action-row">
            <button class="button-primary" type="submit" :disabled="isSaving">
              {{ isSaving ? "Saving..." : "Save task" }}
            </button>
          </div>
        </form>

        <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
        <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>
      </section>
    </div>
  </section>
</template>
