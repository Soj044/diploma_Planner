<script setup lang="ts">
import { watch } from "vue";

const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    description?: string;
    wide?: boolean;
  }>(),
  {
    description: "",
    wide: false,
  },
);

const emit = defineEmits<{
  close: [];
}>();

function handleEscape(event: KeyboardEvent) {
  if (event.key === "Escape" && props.open) {
    emit("close");
  }
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      window.addEventListener("keydown", handleEscape);
      return;
    }

    window.removeEventListener("keydown", handleEscape);
  },
  { immediate: true },
);
</script>

<template>
  <div v-if="open" class="modal-root" role="dialog" aria-modal="true" :aria-label="title">
    <div class="modal-backdrop" @click="$emit('close')" />
    <section class="modal-card" :class="{ 'modal-card-wide': wide }">
      <header class="modal-header">
        <div>
          <p class="eyebrow">Workestrator</p>
          <h3 class="modal-title">{{ title }}</h3>
          <p v-if="description" class="page-description">{{ description }}</p>
        </div>
        <button class="button-secondary" type="button" @click="$emit('close')">Close</button>
      </header>

      <div class="modal-body">
        <slot />
      </div>

      <footer v-if="$slots.actions" class="modal-actions">
        <slot name="actions" />
      </footer>
    </section>
  </div>
</template>

<style scoped>
.modal-root {
  inset: 0;
  position: fixed;
  z-index: 30;
}

.modal-backdrop {
  background: rgba(33, 48, 58, 0.55);
  inset: 0;
  position: absolute;
}

.modal-card {
  background: var(--app-surface-strong);
  border: 1px solid var(--app-line);
  border-radius: 1.2rem;
  box-shadow: var(--app-shadow);
  display: grid;
  gap: 1rem;
  inset: 5vh auto auto 50%;
  max-height: 90vh;
  overflow: auto;
  padding: 1.25rem;
  position: relative;
  transform: translateX(-50%);
  width: min(100% - 2rem, 44rem);
}

.modal-card-wide {
  width: min(100% - 2rem, 60rem);
}

.modal-header,
.modal-actions {
  align-items: start;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
}

.modal-title {
  font-size: clamp(1.5rem, 2vw, 2rem);
  line-height: 1.1;
  margin: 0;
}

.modal-body {
  display: grid;
  gap: 1rem;
}

@media (max-width: 900px) {
  .modal-card,
  .modal-card-wide {
    inset: 2vh 1rem auto 1rem;
    transform: none;
    width: auto;
  }

  .modal-header,
  .modal-actions {
    flex-direction: column;
  }
}
</style>
