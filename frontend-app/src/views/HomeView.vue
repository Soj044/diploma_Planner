<script setup lang="ts">
import { computed } from "vue";

import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { useAuth } from "../composables/useAuth";
import { appConfig, frontendAssumptions } from "../config/env";
import { assignmentResources, referenceDataResources, taskResources } from "../services/core-service";
import { plannerResources } from "../services/planner-service";

const auth = useAuth();

const roleHeadline = computed(() => {
  if (auth.role.value === "employee") {
    return "Employee self-service shell";
  }

  if (auth.role.value === "manager") {
    return "Manager workspace over persisted backend flows";
  }

  return "Admin workspace over persisted backend flows";
});

const roleDescription = computed(() => {
  if (auth.role.value === "employee") {
    return "Employee users can review tasks and work only inside self-service schedule and leave routes.";
  }

  return "`core-service` stays the source of truth for business entities and final assignments. `planner-service` keeps persisted plan runs, proposals, and diagnostics. Frontend runtime is aligned with the backend token-auth contract and cookie-compatible local proxy paths.";
});
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Architecture</p>
      <h3 class="page-title">{{ roleHeadline }}</h3>
      <p class="page-description">{{ roleDescription }}</p>
      <div class="pill-row">
        <span class="pill">Core endpoints: {{ referenceDataResources.length + taskResources.length + assignmentResources.length }}</span>
        <span class="pill">Planner endpoints: {{ plannerResources.length }}</span>
        <span class="pill is-warm">/api/v1/auth/*</span>
      </div>
    </section>

    <div class="grid-two">
      <SectionPlaceholder
        eyebrow="What exists now"
        title="App shell and route map"
        description="The frontend now has a stable home in the monorepo with a shared layout and room for the next CRUD slices."
      >
        <ul class="resource-list">
          <li class="resource-item">
            <p class="resource-label">Shared layout</p>
            <p class="resource-copy">Sidebar navigation plus a content area for each MVP section.</p>
          </li>
          <li v-if="auth.role.value !== 'employee'" class="resource-item">
            <p class="resource-label">Reference data CRUD</p>
            <p class="resource-copy">Users, departments, skills, and employees now support list/create/edit/delete from the shell.</p>
          </li>
          <li class="resource-item">
            <p class="resource-label">Task flow</p>
            <p class="resource-copy">Tasks and task requirements now support a connected create/edit/delete flow.</p>
          </li>
          <li v-if="auth.role.value === 'employee'" class="resource-item">
            <p class="resource-label">Self-service routes</p>
            <p class="resource-copy">Employees now get dedicated navigation entries for own schedules and leaves.</p>
          </li>
          <li class="resource-item">
            <p class="resource-label">Thin API layer</p>
            <p class="resource-copy">Dedicated modules for `core-service` and `planner-service` requests.</p>
          </li>
          <li class="resource-item">
            <p class="resource-label">Local proxy</p>
            <p class="resource-copy">{{ frontendAssumptions.proxy }}</p>
          </li>
        </ul>
      </SectionPlaceholder>

      <SectionPlaceholder
        eyebrow="Known gaps"
        title="Still intentionally missing"
        description="This cycle avoids fake browser business logic and keeps unresolved backend/frontend seams visible."
      >
        <ul class="resource-list">
          <li class="resource-item">
            <p class="resource-label">Role-aware access</p>
            <p class="resource-copy">Navigation and routes now respect backend roles at UX level, but screen-level action pruning still needs to be completed.</p>
          </li>
          <li class="resource-item">
            <p class="resource-label">Planning and approval flows</p>
            <p class="resource-copy">
              {{ auth.role.value === "employee"
                ? "Employees remain intentionally excluded from planner launch and assignment approval routes."
                : "Plan runs, proposal review, approvals, and assignments remain ahead after the task flow." }}
            </p>
          </li>
          <li class="resource-item">
            <p class="resource-label">Core API schema UI</p>
            <p class="resource-copy">Planner already has Swagger; core-service still needs manual contract references for frontend work.</p>
          </li>
        </ul>
      </SectionPlaceholder>
    </div>

    <SectionPlaceholder
      eyebrow="Runtime"
      title="Current defaults"
      description="These values come from the frontend env configuration and can be overridden per environment."
    >
      <ul class="key-value-list">
        <li class="key-value-item">
          <span class="key-label">App title</span>
          <span class="key-value">{{ appConfig.appTitle }}</span>
        </li>
        <li class="key-value-item">
          <span class="key-label">Core service URL</span>
          <span class="key-value">{{ appConfig.coreServiceUrl }}</span>
        </li>
        <li class="key-value-item">
          <span class="key-label">Auth contract</span>
          <span class="key-value">{{ frontendAssumptions.auth }}</span>
        </li>
        <li class="key-value-item">
          <span class="key-label">Planner service URL</span>
          <span class="key-value">{{ appConfig.plannerServiceUrl }}</span>
        </li>
      </ul>
    </SectionPlaceholder>
  </div>
</template>
