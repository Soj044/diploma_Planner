<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";

import SectionPlaceholder from "../SectionPlaceholder.vue";
import { coreService } from "../../services/core-service";
import { describeRequestError } from "../../services/http";
import type { Skill, Task, TaskRequirement, TaskRequirementInput } from "../../types/api";

const props = defineProps<{
  selectedTaskId: number | null;
  reloadToken: number;
}>();

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
const errorMessage = ref("");
const successMessage = ref("");

const form = reactive<RequirementFormState>({
  task: "",
  skill: "",
  min_level: 1,
  weight: "1.00",
});

const activeTaskId = computed(() => {
  if (props.selectedTaskId !== null) {
    return props.selectedTaskId;
  }

  return form.task ? Number(form.task) : null;
});

const requirementCountForActiveTask = computed(() => {
  if (activeTaskId.value === null) {
    return requirements.value.length;
  }

  return requirements.value.filter((requirement) => requirement.task === activeTaskId.value).length;
});

const taskNameById = computed(() => {
  return new Map(tasks.value.map((task) => [task.id, task.title]));
});

const skillNameById = computed(() => {
  return new Map(skills.value.map((skill) => [skill.id, skill.name]));
});

const filteredRequirements = computed(() => {
  if (activeTaskId.value === null) {
    return requirements.value;
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

function syncSelectedTask() {
  if (props.selectedTaskId !== null) {
    form.task = String(props.selectedTaskId);
    return;
  }

  if (!form.task && tasks.value.length > 0) {
    form.task = String(tasks.value[0].id);
  }
}

function resetForm() {
  editingId.value = null;
  form.task = props.selectedTaskId === null ? "" : String(props.selectedTaskId);
  form.skill = "";
  form.min_level = 1;
  form.weight = "1.00";
  syncSelectedTask();
}

function startEditing(requirement: TaskRequirement) {
  editingId.value = requirement.id;
  form.task = String(requirement.task);
  form.skill = String(requirement.skill);
  form.min_level = requirement.min_level;
  form.weight = requirement.weight;
  errorMessage.value = "";
  successMessage.value = "";
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
  isSaving.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const payload = buildPayload();
    await (editingId.value === null
      ? coreService.createTaskRequirement(payload)
      : coreService.updateTaskRequirement(editingId.value, payload));

    successMessage.value = editingId.value === null ? "Task requirement created." : "Task requirement updated.";
    resetForm();
    await load();
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
    await coreService.deleteTaskRequirement(id);
    successMessage.value = "Task requirement deleted.";
    if (editingId.value === id) {
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
    title="Skill requirements attach directly to one task"
    description="This editor stays explicit: a requirement is just one `task + skill + min_level + weight` record in core-service."
  >
    <div class="data-layout">
      <form class="editor-card" @submit.prevent="save">
        <div class="editor-header">
          <div>
            <p class="section-caption">{{ editingId === null ? "Create task requirement" : "Edit task requirement" }}</p>
            <p class="resource-path">/task-requirements/</p>
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

        <div v-if="tasks.length === 0" class="notice">
          Create a task first. Requirements only make sense after a task exists.
        </div>
        <div v-else-if="skills.length === 0" class="notice">
          Create at least one skill in Reference Data before adding a task requirement.
        </div>

        <div class="form-grid">
          <label class="field-group field-group-span-2">
            <span class="field-label">Task</span>
            <select v-model="form.task" class="select-input" required>
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

        <div class="action-row">
          <button
            class="button-primary"
            type="submit"
            :disabled="isSaving || tasks.length === 0 || skills.length === 0"
          >
            {{ isSaving ? "Saving..." : editingId === null ? "Create requirement" : "Save requirement" }}
          </button>
        </div>

        <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
        <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>
      </form>

      <div class="records-card">
        <div class="editor-header">
          <div>
            <p class="section-caption">
              {{ activeTaskId === null ? "All task requirements" : `Requirements for ${taskNameById.get(activeTaskId)}` }}
            </p>
            <p class="resource-copy">
              {{ activeTaskId === null ? "Select a task in the task list to focus this section." : "List is automatically filtered by the selected task." }}
            </p>
          </div>
          <span class="pill">{{ requirementCountForActiveTask }} rows</span>
        </div>

        <p v-if="isLoading" class="resource-copy">Loading...</p>
        <p v-else-if="filteredRequirements.length === 0" class="empty-state">No requirements yet.</p>
        <ul v-else class="resource-list">
          <li v-for="requirement in filteredRequirements" :key="requirement.id" class="resource-item">
            <div class="resource-heading">
              <p class="resource-label">{{ skillNameById.get(requirement.skill) || `Skill #${requirement.skill}` }}</p>
              <div class="inline-actions">
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
            <p class="resource-copy">
              Task: {{ taskNameById.get(requirement.task) || `Task #${requirement.task}` }}
              · Minimum level: {{ requirement.min_level }}
              · Weight: {{ requirement.weight }}
            </p>
            <p class="item-meta">Requirement ID {{ requirement.id }}</p>
          </li>
        </ul>
      </div>
    </div>
  </SectionPlaceholder>
</template>
