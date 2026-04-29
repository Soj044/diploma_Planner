<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";

import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { useAuth } from "../composables/useAuth";
import { coreService } from "../services/core-service";
import { describeRequestError } from "../services/http";
import { plannerService, planRunRequestFields, plannerResources, planningWorkflow } from "../services/planner-service";
import type { Department, PlanResponse, Task } from "../types/api";

interface PlanningFormState {
  planning_period_start: string;
  planning_period_end: string;
  department_id: string;
}

const auth = useAuth();
const departments = ref<Department[]>([]);
const tasks = ref<Task[]>([]);
const selectedTaskIds = ref<string[]>([]);
const latestRun = ref<PlanResponse | null>(null);
const isLoading = ref(false);
const isSubmitting = ref(false);
const errorMessage = ref("");
const successMessage = ref("");

const form = reactive<PlanningFormState>({
  planning_period_start: "",
  planning_period_end: "",
  department_id: "",
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

const canSubmit = computed(() => {
  return Boolean(auth.user.value?.id && form.planning_period_start && form.planning_period_end);
});

const selectedTaskCount = computed(() => selectedTaskIds.value.length);

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
    const [departmentRows, taskRows] = await Promise.all([
      coreService.listDepartments(),
      coreService.listTasks(),
    ]);
    departments.value = departmentRows;
    tasks.value = taskRows;
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
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
    latestRun.value = await plannerService.createPlanRun({
      planning_period_start: form.planning_period_start,
      planning_period_end: form.planning_period_end,
      initiated_by_user_id: String(auth.user.value.id),
      department_id: form.department_id || null,
      task_ids: selectedTaskIds.value,
    });

    successMessage.value = "Plan run launched successfully.";
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isSubmitting.value = false;
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
        This slice covers only the manager/admin launch command. Browser code still does not recalculate eligibility,
        scoring, or optimization, and proposal review remains the next dedicated frontend step.
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
                Status: {{ task.status }} · Estimated: {{ task.estimated_hours }}h
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
        The run was persisted in planner-service. Detailed proposal review is intentionally deferred to the next slice.
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

    <div class="grid-two">
      <SectionPlaceholder
        eyebrow="Endpoints"
        title="Planning APIs"
        description="Point 7 wires the launch endpoint. Persisted review remains the next slice."
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
