<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { coreService } from "../../services/core-service";
import { describeRequestError } from "../../services/http";
import type { Assignment, Department, Task } from "../../types/api";

interface AssignmentTaskCard {
  assignmentId: number;
  deadline: string;
  title: string;
  description: string;
  departmentName: string;
  status: string;
  plannedHours: number;
  notes: string;
}

const assignments = ref<Assignment[]>([]);
const tasks = ref<Task[]>([]);
const departments = ref<Department[]>([]);
const isLoading = ref(false);
const errorMessage = ref("");

const taskById = computed(() => {
  return new Map(tasks.value.map((task) => [task.id, task]));
});

const departmentNameById = computed(() => {
  return new Map(departments.value.map((department) => [department.id, department.name]));
});

const cards = computed<AssignmentTaskCard[]>(() => {
  return assignments.value
    .filter((assignment) => !["rejected", "cancelled"].includes(assignment.status))
    .map((assignment) => {
      const task = taskById.value.get(assignment.task);
      const departmentName =
        task?.department === null || task?.department === undefined
          ? "No department"
          : departmentNameById.value.get(task.department) || `#${task.department}`;

      return {
        assignmentId: assignment.id,
        deadline: assignment.end_date,
        title: task?.title || `Task #${assignment.task}`,
        description: task?.description || "Task details are unavailable in the current payload.",
        departmentName,
        status: task?.status || "unknown",
        plannedHours: assignment.planned_hours,
        notes: assignment.notes,
      };
    })
    .sort((left, right) => left.deadline.localeCompare(right.deadline));
});

async function load() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    const [assignmentRows, taskRows, departmentRows] = await Promise.all([
      coreService.listAssignments(),
      coreService.listTasks(),
      coreService.listDepartments(),
    ]);
    assignments.value = assignmentRows;
    tasks.value = taskRows;
    departments.value = departmentRows;
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="page-card">
    <div class="editor-header">
      <div>
        <p class="section-caption">My assignments</p>
        <p class="resource-copy">
          This inbox is driven by employee-scoped assignments and enriched with task and department labels in the
          browser.
        </p>
      </div>
      <div class="inline-actions">
        <span class="pill">{{ cards.length }} active items</span>
        <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
      </div>
    </div>

    <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="resource-copy">Loading assignments and task details...</p>
    <p v-else-if="cards.length === 0" class="empty-state">No active assignments are available right now.</p>
    <ul v-else class="resource-list">
      <li v-for="card in cards" :key="card.assignmentId" class="resource-item">
        <div class="resource-heading">
          <p class="resource-label">{{ card.title }}</p>
          <div class="pill-row">
            <span class="pill is-warm">{{ card.status }}</span>
            <span class="pill">Deadline {{ card.deadline }}</span>
          </div>
        </div>
        <p class="resource-copy">{{ card.description || "No description." }}</p>
        <p class="resource-copy">Department: {{ card.departmentName }}</p>
        <p class="resource-copy">Planned hours: {{ card.plannedHours }}</p>
        <p class="resource-copy">Assignment notes: {{ card.notes || "No notes." }}</p>
      </li>
    </ul>
  </section>
</template>
