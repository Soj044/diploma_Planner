<script setup lang="ts">
import SectionPlaceholder from "../components/SectionPlaceholder.vue";
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Stage 2</p>
      <h3 class="page-title">Departments</h3>
      <p class="page-description">
        This route is now the canonical home for the future department directory. Stage 1 backend already returns
        nested employee summaries, so the next frontend stage can build the directory without inventing a separate read
        model.
      </p>
      <div class="pill-row">
        <span class="pill">/departments</span>
        <span class="pill">GET /api/v1/departments/</span>
      </div>
    </section>

    <SectionPlaceholder
      eyebrow="Directory contract"
      title="Nested employee summaries are now available"
      description="The upcoming directory UI should read departments together with employee summaries from the backend payload, without joining user email or recreating a second browser-side model."
    >
      <div class="notice">
        The Stage 1 payload now includes department employees with `id`, `full_name`, and `position_name`. Email must
        stay out of this directory route.
      </div>
    </SectionPlaceholder>
  </div>
</template>
