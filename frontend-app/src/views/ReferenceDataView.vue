<script setup lang="ts">
import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { referenceDataResources } from "../services/core-service";
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Milestone 1</p>
      <h3 class="page-title">Reference data surface is mapped</h3>
      <p class="page-description">
        These are the dictionaries and employee-side entities the UI must support before task creation becomes useful.
        This slice documents and routes them without inventing frontend-only state.
      </p>
    </section>

    <SectionPlaceholder
      eyebrow="Core-service"
      title="Reference CRUD targets"
      description="Next cycle can turn these cards into actual list/create/edit screens with the same backend contracts."
    >
      <ul class="resource-list">
        <li v-for="resource in referenceDataResources" :key="resource.key" class="resource-item">
          <div class="resource-heading">
            <p class="resource-label">{{ resource.label }}</p>
            <span class="pill" :class="{ 'is-warm': resource.requiresAuth }">
              {{ resource.requiresAuth ? "Auth required" : "Public" }}
            </span>
          </div>
          <p class="resource-path">{{ resource.endpoint }}</p>
          <p class="resource-copy">{{ resource.description }}</p>
          <p class="resource-copy"><strong>Next:</strong> {{ resource.nextStep }}</p>
        </li>
      </ul>
    </SectionPlaceholder>
  </div>
</template>
