<script setup lang="ts">
import SectionPlaceholder from "../components/SectionPlaceholder.vue";
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Employee self-service</p>
      <h3 class="page-title">My leaves</h3>
      <p class="page-description">
        This route is reserved for employee users. The next stage will connect it to own `employee-leaves` records and
        keep approval truth in backend state.
      </p>
    </section>

    <SectionPlaceholder
      eyebrow="Coming next"
      title="Self-service leave CRUD"
      description="Stage 5 will replace this placeholder with the real minimal CRUD flow for employee-owned leave records."
    />
  </div>
</template>
