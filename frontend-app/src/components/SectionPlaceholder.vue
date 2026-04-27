<script setup lang="ts">
defineProps<{
  eyebrow: string;
  title: string;
  description: string;
}>();
</script>

<template>
  <section class="page-card">
    <p class="eyebrow">{{ eyebrow }}</p>
    <h3 class="section-title">{{ title }}</h3>
    <p class="section-copy">{{ description }}</p>
    <div class="section-body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.section-title {
  font-size: 1.35rem;
  line-height: 1.2;
  margin: 0;
}

.section-copy {
  color: var(--app-muted);
  margin: 0.7rem 0 0;
}

.section-body {
  margin-top: 1.1rem;
}
</style>
