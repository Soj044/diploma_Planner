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
        Manager approval now happens from the `Planning` review screen. This route is reserved for the next slice where
        the frontend will render read-only final assignments directly from `core-service`.
      </p>
    </section>

    <SectionPlaceholder
      eyebrow="Core-service"
      title="Assignment endpoints"
      description="Approval is live from `Planning`; this screen still tracks the remaining read-only assignments work."
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
      The frontend still does not own assignment timing.
      Planned hours and dates continue to come from the persisted planner proposal during approval.
    </div>
  </div>
</template>
