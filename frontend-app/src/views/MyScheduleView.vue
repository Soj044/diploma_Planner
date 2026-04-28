<script setup lang="ts">
import SectionPlaceholder from "../components/SectionPlaceholder.vue";
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Employee self-service</p>
      <h3 class="page-title">My work schedules</h3>
      <p class="page-description">
        This route is reserved for employee users. The next stage will wire it to own `work-schedules` and
        `work-schedule-days` records using `me.employee_id`.
      </p>
    </section>

    <SectionPlaceholder
      eyebrow="Coming next"
      title="Self-service schedule CRUD"
      description="Stage 5 will replace this placeholder with the real minimal CRUD flow for employee-owned schedules."
    />
  </div>
</template>
