<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";

import DialogModal from "../DialogModal.vue";
import SectionPlaceholder from "../SectionPlaceholder.vue";
import { useAuth } from "../../composables/useAuth";
import { coreService } from "../../services/core-service";
import { describeRequestError } from "../../services/http";
import type { Skill, Task, TaskRequirement, TaskRequirementInput } from "../../types/api";

const props = defineProps<{
  selectedTaskId: number | null;
  reloadToken: number;
}>();

const auth = useAuth();

interface RequirementFormState {
  task: string;
  skill: string;
  min_level: number;
  weight: string;
}

const tasks = ref<Task[]>([]);
const skills = ref<Skill[]>([]);
const requirements = ref<TaskRequirement[]>([]);
const isLoading = ref(false);
const isSaving = ref(false);
const deletingId = ref<number | null>(null);
const editingId = ref<number | null>(null);
const isModalOpen = ref(false);
const errorMessage = ref("");
const successMessage = ref("");

const form = reactive<RequirementFormState>({
  task: "",
  skill: "",
  min_level: 1,
  weight: "1.00",
});

const canManageRequirements = computed(() => {
  return auth.role.value === "admin" || auth.role.value === "manager";
});

const activeTaskId = computed(() => props.selectedTaskId);

const activeTask = computed(() => {
  return tasks.value.find((task) => task.id === activeTaskId.value) || null;
});

const requirementCountForActiveTask = computed(() => {
  if (activeTaskId.value === null) {
    return 0;
  }

  return requirements.value.filter((requirement) => requirement.task === activeTaskId.value).length;
});

const skillNameById = computed(() => {
  return new Map(skills.value.map((skill) => [skill.id, skill.name]));
});

const filteredRequirements = computed(() => {
  if (activeTaskId.value === null) {
    return [];
  }

  return requirements.value.filter((requirement) => requirement.task === activeTaskId.value);
});

const availableSkills = computed(() => {
  const currentTask = form.task ? Number(form.task) : null;

  if (currentTask === null) {
    return skills.value;
  }

  const reservedSkills = new Set(
    requirements.value
      .filter((requirement) => requirement.task === currentTask && requirement.id !== editingId.value)
      .map((requirement) => requirement.skill),
  );

  return skills.value.filter((skill) => !reservedSkills.has(skill.id));
});

const modalTitle = computed(() => {
  return editingId.value === null ? "Add requirement" : "Edit requirement";
});

function syncSelectedTask() {
  form.task = props.selectedTaskId === null ? "" : String(props.selectedTaskId);
}

function closeModal() {
  isModalOpen.value = false;
  editingId.value = null;
}

function resetForm() {
  editingId.value = null;
  form.skill = "";
  form.min_level = 1;
  form.weight = "1.00";
  syncSelectedTask();
}

function openCreateModal() {
  if (!canManageRequirements.value || activeTaskId.value === null) {
    return;
  }

  resetForm();
  errorMessage.value = "";
  successMessage.value = "";
  isModalOpen.value = true;
}

function startEditing(requirement: TaskRequirement) {
  if (!canManageRequirements.value) {
    return;
  }

  editingId.value = requirement.id;
  form.task = String(requirement.task);
  form.skill = String(requirement.skill);
  form.min_level = requirement.min_level;
  form.weight = requirement.weight;
  errorMessage.value = "";
  successMessage.value = "";
  isModalOpen.value = true;
}

async function load() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    const [taskRows, skillRows, requirementRows] = await Promise.all([
      coreService.listTasks(),
      coreService.listSkills(),
      coreService.listTaskRequirements(),
    ]);
    tasks.value = taskRows;
    skills.value = skillRows;
    requirements.value = requirementRows;
    syncSelectedTask();

    if (editingId.value !== null && !requirements.value.some((requirement) => requirement.id === editingId.value)) {
      closeModal();
      resetForm();
    }
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

function buildPayload(): TaskRequirementInput {
  return {
    task: Number(form.task),
    skill: Number(form.skill),
    min_level: Number(form.min_level),
    weight: form.weight.trim() || "1.00",
  };
}

async function save() {
  if (!canManageRequirements.value) {
    return;
  }

  isSaving.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const payload = buildPayload();
    await (editingId.value === null
      ? coreService.createTaskRequirement(payload)
      : coreService.updateTaskRequirement(editingId.value, payload));

    successMessage.value = editingId.value === null ? "Task requirement created." : "Task requirement updated.";
    closeModal();
    resetForm();
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isSaving.value = false;
  }
}

async function remove(id: number) {
  if (!canManageRequirements.value) {
    return;
  }

  deletingId.value = id;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    await coreService.deleteTaskRequirement(id);
    successMessage.value = "Task requirement deleted.";
    if (editingId.value === id) {
      closeModal();
      resetForm();
    }
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    deletingId.value = null;
  }
}

watch(
  () => props.selectedTaskId,
  () => {
    syncSelectedTask();
  },
);

watch(
  () => props.reloadToken,
  () => {
    void load();
  },
);

onMounted(async () => {
  await load();
  resetForm();
});
</script>

<template>
  <SectionPlaceholder
    eyebrow="Task Requirements"
    title="Skill requirements"
    description="Select a task to review the skill expectations that planner will use for matching and scoring."
  >
    <div class="editor-header">
      <div>
        <p class="section-caption">
          {{ activeTask ? `Requirements for ${activeTask.title}` : "Requirements focus" }}
        </p>
        <p class="resource-copy">
          {{
            activeTask
              ? "This list is scoped to the task currently focused in the task board."
              : "Choose a task in the board above to open its requirement set."
          }}
        </p>
      </div>
      <div class="inline-actions">
        <span class="pill">{{ requirementCountForActiveTask }} requirements</span>
        <button
          v-if="canManageRequirements"
          class="button-primary"
          type="button"
          :disabled="activeTaskId === null || skills.length === 0"
          @click="openCreateModal"
        >
          Add requirement
        </button>
        <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
      </div>
    </div>

    <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
    <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>

    <div v-if="activeTaskId === null" class="notice">
      Focus a task in the board first. Requirement editing stays intentionally scoped to one task at a time.
    </div>
    <p v-else-if="isLoading" class="resource-copy">Loading requirements and skills...</p>
    <div v-else-if="skills.length === 0" class="notice">
      Create at least one skill in Admin before adding requirements to this task.
    </div>
    <p v-else-if="filteredRequirements.length === 0" class="empty-state">No requirements have been added to this task yet.</p>
    <ul v-else class="resource-list">
      <li v-for="requirement in filteredRequirements" :key="requirement.id" class="resource-item">
        <div class="resource-heading">
          <p class="resource-label">{{ skillNameById.get(requirement.skill) || `Skill #${requirement.skill}` }}</p>
          <div v-if="canManageRequirements" class="inline-actions">
            <button class="button-secondary" type="button" @click="startEditing(requirement)">Edit</button>
            <button
              class="button-danger"
              type="button"
              :disabled="deletingId === requirement.id"
              @click="remove(requirement.id)"
            >
              {{ deletingId === requirement.id ? "Deleting..." : "Delete" }}
            </button>
          </div>
        </div>
        <div class="pill-row">
          <span class="pill">Level {{ requirement.min_level }}</span>
          <span class="pill">Weight {{ requirement.weight }}</span>
        </div>
      </li>
    </ul>

    <DialogModal
      :open="isModalOpen"
      :title="modalTitle"
      description="Requirement edits stay attached to the focused task and remain read-only for employees."
      @close="closeModal"
    >
      <form class="page-stack" @submit.prevent="save">
        <div class="form-grid">
          <label class="field-group field-group-span-2">
            <span class="field-label">Task</span>
            <select v-model="form.task" class="select-input" :disabled="activeTaskId !== null" required>
              <option value="">Select task</option>
              <option v-for="task in tasks" :key="task.id" :value="String(task.id)">{{ task.title }}</option>
            </select>
          </label>

          <label class="field-group">
            <span class="field-label">Skill</span>
            <select v-model="form.skill" class="select-input" required>
              <option value="">Select skill</option>
              <option v-for="skill in availableSkills" :key="skill.id" :value="String(skill.id)">{{ skill.name }}</option>
              <option
                v-if="
                  editingId !== null &&
                  form.skill &&
                  !availableSkills.some((skill) => String(skill.id) === form.skill) &&
                  skillNameById.get(Number(form.skill))
                "
                :value="form.skill"
              >
                {{ skillNameById.get(Number(form.skill)) }}
              </option>
            </select>
          </label>

          <label class="field-group">
            <span class="field-label">Minimum level</span>
            <input v-model.number="form.min_level" class="text-input" min="1" type="number" required />
          </label>

          <label class="field-group">
            <span class="field-label">Weight</span>
            <input v-model.trim="form.weight" class="text-input" inputmode="decimal" required />
          </label>
        </div>
      </form>

      <template #actions>
        <button class="button-secondary" type="button" :disabled="isSaving" @click="closeModal">Cancel</button>
        <button class="button-primary" type="button" :disabled="isSaving" @click="save">
          {{ isSaving ? "Saving..." : editingId === null ? "Create requirement" : "Save requirement" }}
        </button>
      </template>
    </DialogModal>
  </SectionPlaceholder>
</template>
