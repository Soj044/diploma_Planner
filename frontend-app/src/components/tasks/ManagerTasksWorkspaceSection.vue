<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";

import DialogModal from "../DialogModal.vue";
import { useAuth } from "../../composables/useAuth";
import { coreService } from "../../services/core-service";
import { describeRequestError } from "../../services/http";
import { consumeUiFlash } from "../../services/ui-flash-service";
import type { Department, Task, TaskInput } from "../../types/api";
import { normalizeOptionalNumericInput, type OptionalNumericInput } from "./taskFormNumbers";
import { priorityPillClass } from "./taskPriority";

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
const editingId = ref<number | null>(null);
const isLoading = ref(false);
const isSaving = ref(false);
const deletingId = ref<number | null>(null);
const isEditModalOpen = ref(false);
const errorMessage = ref("");
const successMessage = ref("");

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

const departmentNameById = computed(() => {
  return new Map(departments.value.map((department) => [department.id, department.name]));
});

const canDeleteTasks = computed(() => auth.role.value === "admin");
const isDoneStatus = computed(() => form.status === "done");
const selectedTask = computed(() => visibleTasks.value.find((task) => task.id === selectedTaskId.value) || null);

const visibleTasks = computed(() => {
  if (auth.role.value === "admin") {
    return [...tasks.value].sort((left, right) => right.updated_at.localeCompare(left.updated_at));
  }
  const currentUserId = auth.user.value?.id;
  return [...tasks.value]
    .filter((task) => task.created_by_user === currentUserId)
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at));
});

function setSelectedTask(taskId: number | null) {
  selectedTaskId.value = taskId;
  emit("selected-task-change", taskId);
}

function closeEditModal() {
  isEditModalOpen.value = false;
  editingId.value = null;
}

function resetForm() {
  editingId.value = null;
  form.department = "";
  form.title = "";
  form.description = "";
  form.status = "planned";
  form.priority = "medium";
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
  form.actual_hours = task.actual_hours === null ? "" : String(task.actual_hours);
  form.start_date = task.start_date || "";
  form.due_date = task.due_date;
  setSelectedTask(task.id);
  errorMessage.value = "";
  successMessage.value = "";
  isEditModalOpen.value = true;
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
    created_by_user: auth.user.value?.id ?? 0,
  };
}

async function load() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    const [taskRows, departmentRows] = await Promise.all([coreService.listTasks(), coreService.listDepartments()]);
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
    const updatedTask = await coreService.updateTask(editingId.value, buildPayload());
    successMessage.value = "Task updated.";
    setSelectedTask(updatedTask.id);
    closeEditModal();
    resetForm();
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
      closeEditModal();
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
          Keep the board in focus, jump into requirements from a specific card, and open edit details only when you
          need them.
        </p>
      </div>
      <div class="inline-actions">
        <RouterLink class="button-primary" to="/tasks/new">Create task</RouterLink>
        <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
      </div>
    </div>

    <div class="workspace-summary">
      <span class="pill">{{ visibleTasks.length }} tasks in scope</span>
      <span v-if="selectedTask" class="pill">Focused: {{ selectedTask.title }}</span>
    </div>

    <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
    <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>

    <section class="records-card">
      <div class="editor-header">
        <div>
          <p class="task-board-kicker">Task board</p>
          <h3 class="task-board-title">Plan-visible tasks</h3>
          <p class="resource-copy">Use a card to focus requirements, inspect timing, or open the task editor.</p>
        </div>
      </div>

      <p v-if="isLoading" class="resource-copy">Loading tasks...</p>
      <p v-else-if="visibleTasks.length === 0" class="empty-state">No tasks are available in this scope yet.</p>
      <div v-else class="task-board-grid">
        <article
          v-for="task in visibleTasks"
          :key="task.id"
          class="task-card"
          :class="{ 'is-selected': selectedTaskId === task.id }"
        >
          <div class="task-card-topline">
            <span class="task-card-id">Task #{{ task.id }}</span>
            <span class="task-card-updated">Updated {{ new Date(task.updated_at).toLocaleDateString() }}</span>
          </div>

          <div class="task-card-header">
            <h4 class="task-card-title">{{ task.title }}</h4>
            <div class="pill-row">
              <span class="pill">{{ task.status }}</span>
              <span class="pill" :class="priorityPillClass(task.priority)">{{ task.priority }}</span>
            </div>
          </div>

          <p class="task-card-description">
            {{ task.description || "No description yet. Use the edit modal to add more planning context." }}
          </p>

          <div class="task-card-meta">
            <p>
              Department:
              {{ task.department === null ? "None" : departmentNameById.get(task.department) || `#${task.department}` }}
            </p>
            <p>Start: {{ task.start_date || "Not set" }}</p>
            <p>Due: {{ task.due_date }}</p>
            <p v-if="task.actual_hours !== null">Actual: {{ task.actual_hours }}h</p>
          </div>

          <div class="task-card-actions">
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
        </article>
      </div>
    </section>

    <DialogModal
      :open="isEditModalOpen"
      :title="editingId === null ? 'Edit task' : `Edit task #${editingId}`"
      description="Adjust task details without leaving the board. Requirements stay focused in the main workspace."
      @close="closeEditModal"
    >
      <form class="page-stack" @submit.prevent="save">
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
      </form>

      <template #actions>
        <button class="button-secondary" type="button" :disabled="isSaving" @click="closeEditModal">Cancel</button>
        <button class="button-primary" type="button" :disabled="isSaving" @click="save">
          {{ isSaving ? "Saving..." : "Save task" }}
        </button>
      </template>
    </DialogModal>
  </section>
</template>

<style scoped>
.workspace-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1rem;
}

.task-board-kicker {
  color: var(--app-accent);
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  margin: 0;
  text-transform: uppercase;
}

.task-board-title {
  font-size: clamp(1.45rem, 2vw, 2rem);
  line-height: 1.05;
  margin: 0.2rem 0 0;
}

.task-board-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr));
}

.task-card {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.85), rgba(255, 252, 247, 0.95));
  border: 1px solid var(--app-line);
  border-radius: 1.2rem;
  box-shadow: var(--app-shadow);
  display: grid;
  gap: 0.85rem;
  padding: 1rem;
  transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
}

.task-card:hover {
  transform: translateY(-2px);
}

.task-card.is-selected {
  border-color: rgba(16, 125, 103, 0.45);
  box-shadow: 0 0 0 1px rgba(16, 125, 103, 0.12), var(--app-shadow);
}

.task-card-topline,
.task-card-actions {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  justify-content: space-between;
}

.task-card-id,
.task-card-updated {
  color: var(--app-muted);
  font-size: 0.8rem;
}

.task-card-header {
  display: grid;
  gap: 0.65rem;
}

.task-card-title {
  font-size: 1.15rem;
  line-height: 1.15;
  margin: 0;
}

.task-card-description,
.task-card-meta p {
  color: var(--app-muted);
  margin: 0;
}

.task-card-meta {
  display: grid;
  gap: 0.3rem;
}

.task-card-actions {
  justify-content: start;
}
</style>
