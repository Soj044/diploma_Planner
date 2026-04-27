<script setup lang="ts">
import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { taskResources } from "../services/core-service";
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Task Flow</p>
      <h3 class="page-title">Tasks stay anchored in core-service</h3>
      <p class="page-description">
        Task creation and task requirements belong to the core business truth. The frontend will stay thin here too:
        collect manager input, submit DRF payloads, and surface validation from the backend.
      </p>
    </section>

    <SectionPlaceholder
      eyebrow="Contracts"
      title="Task-related endpoints"
      description="The next implementation slice can attach real forms to these endpoints without changing planner behavior."
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
      Task creation will need authenticated core-service access and a manager user ID for `created_by_user`.
      This is one reason the auth gap is kept explicit in the shell instead of hidden in a fake browser state.
    </div>
  </div>
</template>
