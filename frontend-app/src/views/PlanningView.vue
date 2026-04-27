<script setup lang="ts">
import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { planRunRequestFields, plannerResources, planningWorkflow } from "../services/planner-service";
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Planner-service</p>
      <h3 class="page-title">Planning review stays proposal-based</h3>
      <p class="page-description">
        Browser code will never recalculate eligibility, scoring, or optimization.
        It will only submit run commands and render persisted planner artifacts returned by backend contracts.
      </p>
    </section>

    <div class="grid-two">
      <SectionPlaceholder
        eyebrow="Endpoints"
        title="Planning APIs"
        description="Two planner endpoints are enough for the first manager-facing review flow."
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
      description="The client only orchestrates manager actions around persisted backend flow."
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
