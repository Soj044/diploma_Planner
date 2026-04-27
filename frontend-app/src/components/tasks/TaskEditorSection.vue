<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import SectionPlaceholder from "../SectionPlaceholder.vue";
import { coreService } from "../../services/core-service";
import { describeRequestError } from "../../services/http";
import type { Department, Task, TaskInput, User } from "../../types/api";

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
  created_by_user: string;
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

const tasks = ref<Task[]>([]);
const departments = ref<Department[]>([]);
const users = ref<User[]>([]);
const selectedTaskId = ref<number | null>(null);
const isLoading = ref(false);
const isSaving = ref(false);
const deletingId = ref<number | null>(null);
const editingId = ref<number | null>(null);
const errorMessage = ref("");
const successMessage = ref("");

const form = reactive<TaskFormState>({
  department: "",
  title: "",
  description: "",
  status: "draft",
  priority: "medium",
  estimated_hours: 8,
  actual_hours: "",
  start_date: "",
  due_date: "",
  created_by_user: "",
});

const creatorOptions = computed(() => {
  const privilegedUsers = users.value.filter((user) => ["admin", "manager"].includes(user.role));
  return privilegedUsers.length > 0 ? privilegedUsers : users.value;
});

const departmentNameById = computed(() => {
  return new Map(departments.value.map((department) => [department.id, department.name]));
});

const userNameById = computed(() => {
  return new Map(users.value.map((user) => [user.id, user.email]));
});

function syncDefaultCreator() {
  if (!form.created_by_user && creatorOptions.value.length > 0) {
    form.created_by_user = String(creatorOptions.value[0].id);
  }
}

function resetForm() {
  form.department = "";
  form.title = "";
  form.description = "";
  form.status = "draft";
  form.priority = "medium";
  form.estimated_hours = 8;
  form.actual_hours = "";
  form.start_date = "";
  form.due_date = "";
  form.created_by_user = "";
  editingId.value = null;
  syncDefaultCreator();
}

function setSelectedTask(taskId: number | null) {
  selectedTaskId.value = taskId;
  emit("selected-task-change", taskId);
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
  form.created_by_user = String(task.created_by_user);
  setSelectedTask(task.id);
  errorMessage.value = "";
  successMessage.value = "";
}

async function load() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    const [taskRows, departmentRows, userRows] = await Promise.all([
      coreService.listTasks(),
      coreService.listDepartments(),
      coreService.listUsers(),
    ]);
    tasks.value = taskRows;
    departments.value = departmentRows;
    users.value = userRows;
    syncDefaultCreator();

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
    created_by_user: Number(form.created_by_user),
  };
}

async function save() {
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

onMounted(load);
</script>

<template>
  <SectionPlaceholder
    eyebrow="Tasks"
    title="Task creation stays inside core-service truth"
    description="Managers can now create and maintain planner-visible tasks directly in the frontend shell."
  >
    <div class="data-layout">
      <form class="editor-card" @submit.prevent="save">
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

        <div v-if="creatorOptions.length === 0" class="notice">
          Create at least one manager or admin user in Reference Data before creating tasks.
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

          <label class="field-group field-group-span-2">
            <span class="field-label">Created by user</span>
            <select v-model="form.created_by_user" class="select-input" required>
              <option value="">Select creator</option>
              <option v-for="user in creatorOptions" :key="user.id" :value="String(user.id)">
                {{ user.email }} · {{ user.role }}
              </option>
            </select>
          </label>
        </div>

        <div class="action-row">
          <button class="button-primary" type="submit" :disabled="isSaving || creatorOptions.length === 0">
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
                <button class="button-secondary" type="button" @click="startEditing(task)">Edit</button>
                <button
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
              {{ userNameById.get(task.created_by_user) || `#${task.created_by_user}` }}
            </p>
            <p class="resource-copy">
              Estimated: {{ task.estimated_hours }}h
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
