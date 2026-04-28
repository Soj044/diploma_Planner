<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";

import { useAuth } from "../composables/useAuth";
import { appConfig, frontendAssumptions } from "../config/env";

const route = useRoute();
const router = useRouter();
const auth = useAuth();

const navigation = [
  {
    label: "Shell",
    to: "/",
  },
  {
    label: "Reference Data",
    to: "/reference-data",
  },
  {
    label: "Tasks",
    to: "/tasks",
  },
  {
    label: "Planning",
    to: "/planning",
  },
  {
    label: "Assignments",
    to: "/assignments",
  },
] as const;

const pageTitle = computed(() => {
  return typeof route.meta.title === "string" ? route.meta.title : "Workestrator";
});

const sessionLabel = computed(() => {
  if (!auth.user.value) {
    return "No session";
  }

  return `${auth.user.value.email} · ${auth.user.value.role}`;
});

async function handleLogout() {
  await auth.logout();
  await router.push({ name: "login" });
}
</script>

<template>
  <div class="shell">
    <aside class="shell-sidebar">
      <div class="brand-card">
        <p class="brand-kicker">Workestrator</p>
        <h1 class="brand-title">Frontend MVP Shell</h1>
        <p class="brand-copy">
          Thin Vue client over existing `core-service` and `planner-service` contracts.
        </p>
        <div class="pill-row">
          <span class="pill">Vue 3 + TypeScript</span>
          <span class="pill is-warm">Token auth flow</span>
        </div>
      </div>

      <nav class="nav-card" aria-label="Main navigation">
        <RouterLink
          v-for="item in navigation"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ 'is-active': route.path === item.to }"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="meta-card">
        <p class="meta-title">Runtime config</p>
        <ul class="key-value-list">
          <li class="key-value-item">
            <span class="key-label">Session</span>
            <span class="key-value">{{ sessionLabel }}</span>
          </li>
          <li class="key-value-item">
            <span class="key-label">Core API</span>
            <span class="key-value">{{ appConfig.coreServiceUrl }}</span>
          </li>
          <li class="key-value-item">
            <span class="key-label">Planner API</span>
            <span class="key-value">{{ appConfig.plannerServiceUrl }}</span>
          </li>
          <li class="key-value-item">
            <span class="key-label">Auth path</span>
            <span class="key-value">/api/v1/auth/*</span>
          </li>
        </ul>
        <div class="action-row">
          <button class="button-secondary" type="button" @click="handleLogout">Logout</button>
        </div>
      </div>
    </aside>

    <main class="shell-main">
      <header class="topbar">
        <div>
          <p class="eyebrow">Current Slice</p>
          <h2 class="page-title">{{ pageTitle }}</h2>
        </div>
        <div class="topbar-notes">
          <p>{{ frontendAssumptions.proxy }}</p>
          <p>{{ frontendAssumptions.auth }}</p>
        </div>
      </header>

      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: minmax(18rem, 21rem) minmax(0, 1fr);
  min-height: 100vh;
  padding: 1.5rem;
}

.shell-sidebar {
  display: grid;
  gap: 1rem;
  align-content: start;
}

.brand-card,
.nav-card,
.meta-card,
.topbar {
  backdrop-filter: blur(12px);
  background: var(--app-surface);
  border: 1px solid var(--app-line);
  border-radius: 1.35rem;
  box-shadow: var(--app-shadow);
}

.brand-card,
.meta-card,
.topbar {
  padding: 1.25rem;
}

.brand-kicker {
  color: var(--app-accent);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  margin: 0;
  text-transform: uppercase;
}

.brand-title {
  font-size: 1.8rem;
  line-height: 1.1;
  margin: 0.6rem 0 0;
}

.brand-copy {
  color: var(--app-muted);
  margin: 0.75rem 0 1rem;
}

.nav-card {
  display: grid;
  gap: 0.4rem;
  padding: 0.7rem;
}

.nav-link {
  border-radius: 0.95rem;
  color: var(--app-muted);
  font-weight: 700;
  padding: 0.85rem 1rem;
  transition: background-color 150ms ease, color 150ms ease, transform 150ms ease;
}

.nav-link:hover,
.nav-link:focus-visible {
  background: rgba(16, 125, 103, 0.08);
  color: var(--app-accent);
  outline: none;
  transform: translateX(2px);
}

.nav-link.is-active {
  background: linear-gradient(135deg, rgba(16, 125, 103, 0.16), rgba(16, 125, 103, 0.06));
  color: var(--app-ink);
}

.meta-title {
  font-size: 0.9rem;
  font-weight: 800;
  margin: 0 0 1rem;
}

.shell-main {
  display: grid;
  gap: 1.5rem;
  align-content: start;
}

.topbar {
  align-items: start;
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(0, 1fr) minmax(18rem, 26rem);
}

.topbar-notes {
  display: grid;
  gap: 0.7rem;
}

.topbar-notes p {
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid var(--app-line);
  border-radius: 1rem;
  color: var(--app-muted);
  margin: 0;
  padding: 0.8rem 0.9rem;
}

@media (max-width: 1100px) {
  .shell {
    grid-template-columns: 1fr;
  }

  .topbar {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .shell {
    padding: 1rem;
  }
}
</style>
