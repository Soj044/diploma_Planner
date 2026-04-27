<script setup lang="ts">
import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { assignmentResources } from "../services/core-service";
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Approval Handoff</p>
      <h3 class="page-title">Final assignments remain in core-service</h3>
      <p class="page-description">
        The browser will eventually let a manager choose one persisted proposal and send only the minimal handoff payload.
        `core-service` keeps the authority to reread planner artifacts and create the final `Assignment`.
      </p>
    </section>

    <SectionPlaceholder
      eyebrow="Core-service"
      title="Assignment endpoints"
      description="The upcoming approval screen will be wired to these existing routes."
    >
      <ul class="resource-list">
        <li v-for="resource in assignmentResources" :key="resource.key" class="resource-item">
          <p class="resource-label">{{ resource.label }}</p>
          <p class="resource-path">{{ resource.endpoint }}</p>
          <p class="resource-copy">{{ resource.description }}</p>
          <p class="resource-copy"><strong>Next:</strong> {{ resource.nextStep }}</p>
        </li>
      </ul>
    </SectionPlaceholder>

    <div class="notice">
      The frontend will not send assignment timing as manager-owned state.
      Planned hours and dates must continue to come from the persisted planner proposal during approval.
    </div>
  </div>
</template>
