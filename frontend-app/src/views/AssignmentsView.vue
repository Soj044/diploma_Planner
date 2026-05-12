<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import { useAuth } from "../composables/useAuth";
import { coreService } from "../services/core-service";
import { describeRequestError } from "../services/http";
import type { Assignment, Employee, Task } from "../types/api";

interface AssignmentFilters {
  status: string;
  source_plan_run_id: string;
  search: string;
}

const auth = useAuth();
const assignments = ref<Assignment[]>([]);
const tasks = ref<Task[]>([]);
const employees = ref<Employee[]>([]);
const isLoading = ref(false);
const errorMessage = ref("");

const filters = reactive<AssignmentFilters>({
  status: "",
  source_plan_run_id: "",
  search: "",
});

const taskTitleById = computed(() => {
  return new Map(tasks.value.map((task) => [task.id, task.title]));
});

const employeeNameById = computed(() => {
  return new Map(employees.value.map((employee) => [employee.id, employee.full_name]));
});

const statusOptions = computed(() => {
  return [...new Set(assignments.value.map((assignment) => assignment.status))].sort((left, right) =>
    left.localeCompare(right),
  );
});

const filteredAssignments = computed(() => {
  const search = filters.search.trim().toLowerCase();
  const sourcePlanRunId = filters.source_plan_run_id.trim().toLowerCase();

  return [...assignments.value]
    .sort((left, right) => {
      const leftDate = left.approved_at || left.assigned_at;
      const rightDate = right.approved_at || right.assigned_at;
      return rightDate.localeCompare(leftDate);
    })
    .filter((assignment) => {
      if (filters.status && assignment.status !== filters.status) {
        return false;
      }

      if (sourcePlanRunId) {
        const runId = (assignment.source_plan_run_id || "").toLowerCase();
        if (!runId.includes(sourcePlanRunId)) {
          return false;
        }
      }

      if (!search) {
        return true;
      }

      const taskTitle = taskTitleById.value.get(assignment.task)?.toLowerCase() || "";
      const employeeName = employeeNameById.value.get(assignment.employee)?.toLowerCase() || "";
      const notes = assignment.notes.toLowerCase();

      return (
        taskTitle.includes(search) ||
        employeeName.includes(search) ||
        notes.includes(search) ||
        String(assignment.id).includes(search)
      );
    });
});

const approvedCount = computed(() => {
  return assignments.value.filter((assignment) => assignment.status === "approved").length;
});

const sourcedByPlannerCount = computed(() => {
  return assignments.value.filter((assignment) => Boolean(assignment.source_plan_run_id)).length;
});

async function loadAssignmentsView() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    const [assignmentRows, taskRows, employeeRows] = await Promise.all([
      coreService.listAssignments(),
      coreService.listTasks(),
      coreService.listEmployees(),
    ]);

    assignments.value = assignmentRows;
    tasks.value = taskRows;
    employees.value = employeeRows;
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

onMounted(loadAssignmentsView);
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Assignments</p>
      <h3 class="page-title">Read-only final assignments</h3>
      <p class="page-description">
        Review the assignments that were finally approved and filter them locally without changing the underlying records.
      </p>
      <div class="pill-row">
        <span class="pill is-warm">{{ auth.user.value ? auth.user.value.role : "No auth context" }}</span>
        <span class="pill">{{ filteredAssignments.length }} visible assignments</span>
      </div>
    </section>

    <section class="page-card">
      <div class="data-layout">
        <form class="editor-card" @submit.prevent>
          <div class="editor-header">
            <div>
              <p class="section-caption">Assignment filters</p>
              <p class="resource-copy">
                Filters help narrow the list in the browser and do not change the stored assignments.
              </p>
            </div>
            <div class="inline-actions">
              <button class="button-secondary" type="button" :disabled="isLoading" @click="loadAssignmentsView">
                Refresh list
              </button>
            </div>
          </div>

          <div class="form-grid">
            <label class="field-group">
              <span class="field-label">Status</span>
              <select v-model="filters.status" class="select-input">
                <option value="">All statuses</option>
                <option v-for="status in statusOptions" :key="status" :value="status">
                  {{ status }}
                </option>
              </select>
            </label>

            <label class="field-group">
              <span class="field-label">Source plan run ID</span>
              <input v-model.trim="filters.source_plan_run_id" class="text-input" placeholder="UUID or fragment" />
            </label>

            <label class="field-group field-group-span-2">
              <span class="field-label">Search</span>
              <input
                v-model.trim="filters.search"
                class="text-input"
                placeholder="Task title, employee name, notes, or assignment ID"
              />
            </label>
          </div>

          <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
        </form>

        <div class="records-card">
          <div class="editor-header">
            <div>
              <p class="section-caption">Summary</p>
              <p class="resource-copy">The list below is read-only and reflects only persisted final assignments.</p>
            </div>
            <span class="pill">{{ assignments.length }} total</span>
          </div>

          <ul class="key-value-list">
            <li class="key-value-item">
              <span class="key-label">Approved status count</span>
              <span class="key-value">{{ approvedCount }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Planner-backed assignments</span>
              <span class="key-value">{{ sourcedByPlannerCount }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Manual / non-planner assignments</span>
              <span class="key-value">{{ assignments.length - sourcedByPlannerCount }}</span>
            </li>
          </ul>

          <div class="notice">
            Dates and planned hours shown here come from the saved assignment record. This screen does not recalculate them.
          </div>
        </div>
      </div>
    </section>

    <section class="page-card">
      <div class="editor-header">
        <div>
          <p class="section-caption">Assignments</p>
          <p class="resource-copy">
            Use this route to audit what was finally approved, whether it came from a planning run or a manual fallback.
          </p>
        </div>
        <span class="pill">{{ filteredAssignments.length }} records</span>
      </div>

      <div v-if="isLoading" class="resource-copy">Loading assignments, tasks, and employee labels...</div>
      <p v-else-if="filteredAssignments.length === 0" class="empty-state">
        No assignments match the current filters.
      </p>
      <ul v-else class="resource-list">
        <li v-for="assignment in filteredAssignments" :key="assignment.id" class="resource-item">
          <div class="resource-heading">
            <p class="resource-label">
              {{ taskTitleById.get(assignment.task) || `Task #${assignment.task}` }}
            </p>
            <div class="pill-row">
              <span class="pill is-warm">{{ assignment.status }}</span>
              <span class="pill">assignment #{{ assignment.id }}</span>
            </div>
          </div>

          <p class="resource-copy">
            Employee: {{ employeeNameById.get(assignment.employee) || `Employee #${assignment.employee}` }}
          </p>
          <p class="resource-copy">
            Dates: {{ assignment.start_date }} → {{ assignment.end_date }}
            · Planned hours: {{ assignment.planned_hours }}
          </p>
          <p class="resource-copy">
            Source plan run:
            {{ assignment.source_plan_run_id || "Not linked to a planning run" }}
          </p>
          <p class="resource-copy">
            Assigned by: {{ assignment.assigned_by_type }}
            · Approved by: {{ assignment.approved_by_user ? `User #${assignment.approved_by_user}` : "n/a" }}
          </p>
          <p class="resource-copy">
            Assigned at: {{ new Date(assignment.assigned_at).toLocaleString() }}
            · Approved at:
            {{ assignment.approved_at ? new Date(assignment.approved_at).toLocaleString() : "n/a" }}
          </p>
          <p class="resource-copy">
            Notes: {{ assignment.notes || "No notes." }}
          </p>
        </li>
      </ul>
    </section>

  </div>
</template>
