<script setup lang="ts">
import { computed, ref } from "vue";

import EmployeeTaskInboxSection from "../components/tasks/EmployeeTaskInboxSection.vue";
import ManagerTasksWorkspaceSection from "../components/tasks/ManagerTasksWorkspaceSection.vue";
import TaskRequirementsSection from "../components/tasks/TaskRequirementsSection.vue";
import { useAuth } from "../composables/useAuth";

const auth = useAuth();
const selectedTaskId = ref<number | null>(null);
const taskReloadToken = ref(0);

const taskIntro = computed(() => {
  if (auth.role.value === "employee") {
    return "Employee task visibility now follows assignment truth: the browser joins self-scoped assignments with task and department labels without turning tasks into a second mutable source of truth.";
  }

  return "Managers and admins can focus one task at a time, keep requirements close to the board, and open edit details only when needed.";
});

function handleSelectedTaskChange(taskId: number | null) {
  selectedTaskId.value = taskId;
}

function handleTasksUpdated() {
  taskReloadToken.value += 1;
}
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Task Flow</p>
      <h3 class="page-title">Task board and requirements</h3>
      <p class="page-description">{{ taskIntro }}</p>
      <div class="pill-row">
        <span class="pill is-warm">{{ selectedTaskId === null ? "No task selected" : `Focused task #${selectedTaskId}` }}</span>
      </div>
    </section>

    <EmployeeTaskInboxSection v-if="auth.role.value === 'employee'" />

    <template v-else>
      <ManagerTasksWorkspaceSection
        @selected-task-change="handleSelectedTaskChange"
        @tasks-updated="handleTasksUpdated"
      />

      <TaskRequirementsSection
        :selected-task-id="selectedTaskId"
        :reload-token="taskReloadToken"
      />
    </template>
  </div>
</template>
