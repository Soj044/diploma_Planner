<script setup lang="ts">
import { ref } from "vue";

import TaskEditorSection from "../components/tasks/TaskEditorSection.vue";
import TaskRequirementsSection from "../components/tasks/TaskRequirementsSection.vue";
import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { taskResources } from "../services/core-service";

const selectedTaskId = ref<number | null>(null);
const taskReloadToken = ref(0);

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
      <p class="page-description">
        Tasks and task requirements belong to the core business truth. The frontend now lets a manager create both parts
        of that flow without re-implementing any planner logic in the browser.
      </p>
      <div class="pill-row">
        <span class="pill">/tasks/</span>
        <span class="pill">/task-requirements/</span>
        <span class="pill is-warm">{{ selectedTaskId === null ? "No task selected" : `Focused task #${selectedTaskId}` }}</span>
      </div>
    </section>

    <TaskEditorSection
      @selected-task-change="handleSelectedTaskChange"
      @tasks-updated="handleTasksUpdated"
    />

    <TaskRequirementsSection
      :selected-task-id="selectedTaskId"
      :reload-token="taskReloadToken"
    />

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
      The next auth migration stage will replace the explicit `created_by_user` picker with the authenticated user from
      `/api/v1/auth/me`.
    </div>
  </div>
</template>
