<script setup lang="ts">
import EmployeesSection from "../components/reference-data/EmployeesSection.vue";
import SimpleCatalogSection from "../components/reference-data/SimpleCatalogSection.vue";
import UserAccountsSection from "../components/reference-data/UserAccountsSection.vue";
import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { coreService, referenceDataResources } from "../services/core-service";

const deferredResources = referenceDataResources.filter((resource) => {
  return !["users", "departments", "skills", "employees"].includes(resource.key);
});
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Milestone 1</p>
      <h3 class="page-title">Reference data CRUD is now live for task prerequisites</h3>
      <p class="page-description">
        This cycle covers the minimal reference entities needed before task creation: `users`, `departments`, `skills`,
        and `employees`. The browser still stays thin and surfaces backend validation instead of re-implementing rules.
      </p>
      <div class="pill-row">
        <span class="pill">/users/</span>
        <span class="pill">/departments/</span>
        <span class="pill">/skills/</span>
        <span class="pill">/employees/</span>
      </div>
    </section>

    <UserAccountsSection />

    <SimpleCatalogSection
      eyebrow="Departments"
      title="Departments for employee and task grouping"
      description="Managers can now maintain task-owning departments directly from the frontend shell."
      endpoint="/departments/"
      entity-label="department"
      :load-items="coreService.listDepartments"
      :create-item="coreService.createDepartment"
      :update-item="coreService.updateDepartment"
      :delete-item="coreService.deleteDepartment"
    />

    <SimpleCatalogSection
      eyebrow="Skills"
      title="Skills used later by task requirements"
      description="This CRUD slice gives task requirements a maintained skill vocabulary before task forms arrive."
      endpoint="/skills/"
      entity-label="skill"
      :load-items="coreService.listSkills"
      :create-item="coreService.createSkill"
      :update-item="coreService.updateSkill"
      :delete-item="coreService.deleteSkill"
    />

    <EmployeesSection />

    <SectionPlaceholder
      eyebrow="Deferred within reference data"
      title="Planning-facing entities still follow after task prerequisites"
      description="These endpoints stay explicit in the backlog, but they are intentionally not bundled into this first CRUD cut."
    >
      <ul class="resource-list">
        <li v-for="resource in deferredResources" :key="resource.key" class="resource-item">
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
