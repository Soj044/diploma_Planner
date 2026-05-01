<script setup lang="ts">
import { computed } from "vue";

import { useAuth } from "../composables/useAuth";

const auth = useAuth();

const employeeProfile = computed(() => auth.user.value?.employee_profile ?? null);

const profileStatus = computed(() => {
  if (!auth.user.value) {
    return "No active session";
  }

  if (employeeProfile.value?.is_active === false) {
    return "Employee profile inactive";
  }

  return "Active";
});

const roleBadgeLabel = computed(() => {
  if (!auth.user.value?.role) {
    return "No role";
  }

  return `${auth.user.value.role.charAt(0).toUpperCase()}${auth.user.value.role.slice(1)} role`;
});
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Profile</p>
      <h3 class="page-title">Current user profile</h3>
      <p class="page-description">
        This screen stays thin and reads only from the authenticated frontend session payload returned by
        `core-service`.
      </p>
      <div class="pill-row">
        <span class="pill">/profile</span>
        <span v-if="auth.role.value" class="pill is-warm">{{ roleBadgeLabel }}</span>
      </div>
    </section>

    <section class="page-card">
      <div class="grid-two">
        <div class="editor-card">
          <p class="section-caption">Account</p>
          <ul class="key-value-list">
            <li class="key-value-item">
              <span class="key-label">Email</span>
              <span class="key-value">{{ auth.user.value?.email ?? "No authenticated user" }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Role</span>
              <span class="key-value">{{ auth.user.value?.role ?? "n/a" }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Profile status</span>
              <span class="key-value">{{ profileStatus }}</span>
            </li>
          </ul>
        </div>

        <div class="records-card">
          <p class="section-caption">Employee profile</p>
          <ul class="key-value-list">
            <li class="key-value-item">
              <span class="key-label">Full name</span>
              <span class="key-value">{{ employeeProfile?.full_name ?? "No employee profile" }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Department ID</span>
              <span class="key-value">{{ employeeProfile?.department_id ?? "Unassigned" }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Position</span>
              <span class="key-value">{{ employeeProfile?.position_name ?? "Unassigned" }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Hire date</span>
              <span class="key-value">{{ employeeProfile?.hire_date ?? "Not set" }}</span>
            </li>
            <li class="key-value-item">
              <span class="key-label">Employee active</span>
              <span class="key-value">{{ employeeProfile ? (employeeProfile.is_active ? "Yes" : "No") : "n/a" }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  </div>
</template>
