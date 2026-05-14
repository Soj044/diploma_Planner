<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { useAuth } from "../composables/useAuth";
import { coreService } from "../services/core-service";
import { describeRequestError } from "../services/http";
import type { Department } from "../types/api";

const auth = useAuth();
const departments = ref<Department[]>([]);
const isLoading = ref(false);
const errorMessage = ref("");

const orderedDepartments = computed(() => {
  return [...departments.value].sort((left, right) => left.name.localeCompare(right.name));
});

const canOpenEmployeeProfiles = computed(() => {
  return auth.role.value === "admin" || auth.role.value === "manager";
});

async function load() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    departments.value = await coreService.listDepartments();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Departments</p>
      <h3 class="page-title">Department directory</h3>
      <p class="page-description">
        Browse teams, see who belongs where, and open employee profiles directly from the directory when your role allows it.
      </p>
    </section>

    <section class="page-card">
      <div class="editor-header">
        <div>
          <p class="section-caption">All departments</p>
          <p class="resource-copy">Each department card includes only employee full names and positions.</p>
        </div>
        <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
      </div>

      <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
      <p v-else-if="isLoading" class="resource-copy">Loading departments...</p>
      <p v-else-if="orderedDepartments.length === 0" class="empty-state">No departments are available.</p>
      <div v-else class="grid-two">
        <section v-for="department in orderedDepartments" :key="department.id" class="records-card">
          <div class="editor-header">
            <div>
              <p class="section-caption">{{ department.name }}</p>
              <p class="resource-copy">{{ department.description || "No description." }}</p>
            </div>
            <span class="pill">{{ department.employees.length }} employees</span>
          </div>

          <p v-if="department.employees.length === 0" class="empty-state">No employees in this department yet.</p>
          <ul v-else class="resource-list">
            <li v-for="employee in department.employees" :key="employee.id" class="resource-item">
              <RouterLink
                v-if="canOpenEmployeeProfiles"
                class="resource-label department-employee-link"
                :to="{ name: 'employee-profile', params: { id: employee.id } }"
              >
                {{ employee.full_name }}
              </RouterLink>
              <p v-else class="resource-label">{{ employee.full_name }}</p>
              <p class="resource-copy">{{ employee.position_name || "Position not set" }}</p>
            </li>
          </ul>
        </section>
      </div>
    </section>
  </div>
</template>

<style scoped>
.department-employee-link:hover,
.department-employee-link:focus-visible {
  color: var(--app-accent);
  outline: none;
}
</style>
