<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";

import { useAuth } from "../composables/useAuth";
import type { AuthRole } from "../types/api";

const route = useRoute();
const router = useRouter();
const auth = useAuth();

interface NavigationItem {
  label: string;
  to: string;
  roles: AuthRole[];
}

const navigation: NavigationItem[] = [
  {
    label: "Tasks",
    to: "/tasks",
    roles: ["admin", "manager", "employee"],
  },
  {
    label: "Schedule",
    to: "/schedule",
    roles: ["admin", "manager", "employee"],
  },
  {
    label: "Leaves",
    to: "/leaves",
    roles: ["admin", "manager", "employee"],
  },
  {
    label: "Departments",
    to: "/departments",
    roles: ["admin", "manager", "employee"],
  },
  {
    label: "Profile",
    to: "/profile",
    roles: ["admin", "manager", "employee"],
  },
  {
    label: "Admin",
    to: "/admin",
    roles: ["admin"],
  },
];

const pageTitle = computed(() => {
  return typeof route.meta.title === "string" ? route.meta.title : "Workestrator";
});

const visibleNavigation = computed(() => {
  const role = auth.role.value;
  return navigation.filter((item) => role !== null && item.roles.includes(role));
});

function isNavigationActive(item: NavigationItem) {
  if (route.path === item.to) {
    return true;
  }

  if (item.to === "/tasks" && route.path === "/tasks/new") {
    return true;
  }

  if (item.to === "/departments" && route.path.startsWith("/employees/")) {
    return true;
  }

  return route.path.startsWith(`${item.to}/`);
}

const sessionLabel = computed(() => {
  if (!auth.user.value) {
    return "No session";
  }

  return auth.user.value.employee_profile?.full_name || auth.user.value.email;
});

const sessionDetails = computed(() => {
  if (!auth.user.value) {
    return "Guest";
  }

  return `${auth.user.value.email} · ${auth.user.value.role}`;
});

const sectionBadges = computed(() => {
  if (!auth.user.value) {
    return [];
  }

  return [auth.user.value.role, auth.user.value.employee_profile?.is_active ? "employee active" : "employee pending"].filter(Boolean);
});

async function handleLogout() {
  await auth.logout();
  await router.push({ name: "login" });
}
</script>

<template>
  <div class="shell">
    <header class="shell-topbar">
      <RouterLink class="brand-link" to="/tasks">
        <span class="brand-mark">Workestrator</span>
        <span class="brand-copy">Operational planning frontend</span>
      </RouterLink>

      <nav class="top-nav" aria-label="Main navigation">
        <RouterLink
          v-for="item in visibleNavigation"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ 'is-active': isNavigationActive(item) }"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="session-actions">
        <div class="session-card">
          <span class="session-primary">{{ sessionLabel }}</span>
          <span class="session-secondary">{{ sessionDetails }}</span>
        </div>
        <button class="button-secondary logout-button" type="button" @click="handleLogout">Logout</button>
      </div>
    </header>

    <section class="shell-subbar">
      <div>
        <p class="eyebrow">Current Section</p>
        <h2 class="shell-title">{{ pageTitle }}</h2>
      </div>
      <div class="pill-row shell-pills">
        <span v-for="badge in sectionBadges" :key="badge" class="pill">{{ badge }}</span>
      </div>
    </section>

    <main class="shell-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  gap: 1.5rem;
  min-height: 100vh;
  padding: 1.5rem;
}

.shell-topbar,
.shell-subbar {
  align-items: center;
  backdrop-filter: blur(12px);
  background: var(--app-surface);
  border: 1px solid var(--app-line);
  border-radius: 1.35rem;
  box-shadow: var(--app-shadow);
  display: flex;
  gap: 1rem;
}

.shell-topbar {
  justify-content: space-between;
  padding: 1rem 1.25rem;
}

.shell-subbar {
  justify-content: space-between;
  padding: 1rem 1.25rem;
}

.brand-link {
  display: grid;
  gap: 0.18rem;
  min-width: 14rem;
}

.brand-mark {
  color: var(--app-accent);
  font-size: 1.05rem;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.brand-copy {
  color: var(--app-muted);
  font-size: 0.88rem;
}

.top-nav {
  display: flex;
  flex: 1 1 auto;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
}

.nav-link {
  border-radius: 999px;
  color: var(--app-muted);
  font-weight: 800;
  padding: 0.65rem 1rem;
  transition: background-color 150ms ease, color 150ms ease, transform 150ms ease;
}

.nav-link:hover,
.nav-link:focus-visible {
  background: rgba(16, 125, 103, 0.08);
  color: var(--app-accent);
  outline: none;
  transform: translateY(-1px);
}

.nav-link.is-active {
  background: linear-gradient(135deg, rgba(16, 125, 103, 0.16), rgba(16, 125, 103, 0.05));
  color: var(--app-ink);
}

.session-actions {
  align-items: center;
  display: flex;
  gap: 0.8rem;
}

.session-card {
  align-items: end;
  display: grid;
  gap: 0.2rem;
  justify-items: end;
}

.session-primary {
  font-size: 0.95rem;
  font-weight: 800;
}

.session-secondary {
  color: var(--app-muted);
  font-size: 0.8rem;
}

.logout-button {
  white-space: nowrap;
}

.shell-title {
  font-size: clamp(1.4rem, 2vw, 2rem);
  line-height: 1.1;
  margin: 0;
}

.shell-pills {
  justify-content: end;
}

.shell-main {
  display: grid;
  gap: 1.5rem;
  align-content: start;
}

@media (max-width: 1100px) {
  .shell-topbar,
  .shell-subbar {
    align-items: start;
    flex-direction: column;
  }

  .top-nav {
    justify-content: start;
  }

  .session-actions,
  .session-card,
  .shell-pills {
    justify-items: start;
  }
}
</style>
