<script setup lang="ts">
import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { appConfig } from "../config/env";
import { assignmentResources, referenceDataResources, taskResources } from "../services/core-service";
import { plannerResources } from "../services/planner-service";
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Architecture</p>
      <h3 class="page-title">Thin client over persisted backend flows</h3>
      <p class="page-description">
        `core-service` stays the source of truth for business entities and final assignments.
        `planner-service` keeps persisted plan runs, proposals, and diagnostics.
        This first frontend slice only adds the browser shell, routing, and API boundaries on top.
      </p>
      <div class="pill-row">
        <span class="pill">Core endpoints: {{ referenceDataResources.length + taskResources.length + assignmentResources.length }}</span>
        <span class="pill">Planner endpoints: {{ plannerResources.length }}</span>
        <span class="pill is-warm">{{ appConfig.hasCoreServiceAuth ? "Basic auth configured" : "Auth still needs local credentials" }}</span>
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
          <li class="resource-item">
            <p class="resource-label">Thin API layer</p>
            <p class="resource-copy">Dedicated modules for `core-service` and `planner-service` requests.</p>
          </li>
          <li class="resource-item">
            <p class="resource-label">Local proxy</p>
            <p class="resource-copy">Vite proxies `/core-api` and `/planner-api` so the browser can reach both backends during dev.</p>
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
            <p class="resource-label">Dedicated frontend auth flow</p>
            <p class="resource-copy">Local MVP currently assumes explicit Basic auth credentials in `.env.local`.</p>
          </li>
          <li class="resource-item">
            <p class="resource-label">Actual CRUD forms</p>
            <p class="resource-copy">Reference data, tasks, planning runs, and approvals are the next slices on top of this shell.</p>
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
          <span class="key-label">Planner service URL</span>
          <span class="key-value">{{ appConfig.plannerServiceUrl }}</span>
        </li>
      </ul>
    </SectionPlaceholder>
  </div>
</template>
