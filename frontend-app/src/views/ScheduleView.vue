<script setup lang="ts">
import { computed } from "vue";

import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { useAuth } from "../composables/useAuth";

const auth = useAuth();

const title = computed(() => {
  if (auth.role.value === "employee") {
    return "Schedule route is now reserved for employee read-only visibility";
  }

  return "Schedule route is reserved for the manager/admin scheduling workspace";
});

const description = computed(() => {
  if (auth.role.value === "employee") {
    return "Stage 1 backend already moved employee schedules to read-only access. Stage 2 keeps the canonical route and navigation in place without reusing the old CRUD-first screen.";
  }

  return "This route is now the canonical place for future manager/admin scheduling work. Stage 2 installs the final URL and shell entry before the dedicated scheduling UI lands.";
});
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Stage 2</p>
      <h3 class="page-title">Schedule</h3>
      <p class="page-description">{{ description }}</p>
      <div class="pill-row">
        <span class="pill">/schedule</span>
        <span class="pill is-warm">{{ auth.role.value ?? "unknown role" }}</span>
      </div>
    </section>

    <SectionPlaceholder
      eyebrow="Canonical route"
      :title="title"
      description="The browser route and navigation are now final. The dedicated schedule UI follows in the next frontend stage."
    >
      <div class="notice">
        {{ auth.role.value === "employee"
          ? "Do not surface employee schedule CRUD here. Backend truth is already read-only for employee work schedules and schedule days."
          : "Do not rebuild scheduling logic in the browser. The future manager/admin screen must stay a thin client over core-service schedule endpoints." }}
      </div>
    </SectionPlaceholder>
  </div>
</template>
