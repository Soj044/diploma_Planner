<script setup lang="ts">
import { computed, ref } from "vue";

import EmployeeTaskInboxSection from "../components/tasks/EmployeeTaskInboxSection.vue";
import ManagerTasksWorkspaceSection from "../components/tasks/ManagerTasksWorkspaceSection.vue";
import TaskRequirementsSection from "../components/tasks/TaskRequirementsSection.vue";
import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { useAuth } from "../composables/useAuth";
import { taskResources } from "../services/core-service";

const auth = useAuth();
const selectedTaskId = ref<number | null>(null);
const taskReloadToken = ref(0);

const taskIntro = computed(() => {
  if (auth.role.value === "employee") {
    return "Employee task visibility now follows assignment truth: the browser joins self-scoped assignments with task and department labels without turning tasks into a second mutable source of truth.";
  }

  return "Manager and admin users keep an owned task workspace on this route, while the create-and-assign flow now lives on a dedicated /tasks/new screen.";
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
      <h3 class="page-title">Task creation and requirements are now connected</h3>
      <p class="page-description">{{ taskIntro }}</p>
      <div class="pill-row">
        <span class="pill">/tasks/</span>
        <span class="pill">/task-requirements/</span>
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

    <SectionPlaceholder
      eyebrow="Contracts"
      title="Task-related endpoints in this slice"
      description="These routes are now wired into the frontend flow and stay intentionally close to DRF contracts."
    >
      <ul class="resource-list">
        <li v-for="resource in taskResources" :key="resource.key" class="resource-item">
          <p class="resource-label">{{ resource.label }}</p>
          <p class="resource-path">{{ resource.endpoint }}</p>
          <p class="resource-copy">{{ resource.description }}</p>
          <p class="resource-copy"><strong>Next:</strong> {{ resource.nextStep }}</p>
        </li>
      </ul>
    </SectionPlaceholder>

    <div class="notice">
      Task creation now uses the authenticated user from `/api/v1/auth/me` instead of a manual `created_by_user` picker.
    </div>
  </div>
</template>
