<script setup lang="ts">
import { computed } from "vue";

import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { useAuth } from "../composables/useAuth";

const auth = useAuth();

const title = computed(() => {
  if (auth.role.value === "employee") {
    return "Leaves route now follows requested-only self-service rules";
  }

  return "Leaves route is reserved for the requested queue and status actions";
});

const description = computed(() => {
  if (auth.role.value === "employee") {
    return "Stage 1 backend now forces employee leave creation into requested status and allows edits/deletes only while the request stays requested.";
  }

  return "Manager/admin leave review now belongs on a dedicated requested-queue screen backed by the new status action, not on the old employee self-service UI.";
});
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Stage 2</p>
      <h3 class="page-title">Leaves</h3>
      <p class="page-description">{{ description }}</p>
      <div class="pill-row">
        <span class="pill">/leaves</span>
        <span class="pill is-warm">{{ auth.role.value ?? "unknown role" }}</span>
      </div>
    </section>

    <SectionPlaceholder
      eyebrow="Canonical route"
      :title="title"
      description="Stage 2 reserves the route and updates the IA. The role-specific leave UI follows in the next frontend stage."
    >
      <div class="notice">
        {{ auth.role.value === "employee"
          ? "Do not keep a writable leave status selector here. Employee status mutation is no longer a browser-controlled action."
          : "Do not expose generic leave edits here. Manager/admin actions should later use the requested queue plus POST /employee-leaves/{id}/set-status/." }}
      </div>
    </SectionPlaceholder>
  </div>
</template>
