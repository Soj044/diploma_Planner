<script setup lang="ts">
import { computed } from "vue";

import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { useAuth } from "../composables/useAuth";

const auth = useAuth();

const roleHeadline = computed(() => {
  if (auth.role.value === "employee") {
    return "Employee self-service workspace";
  }

  if (auth.role.value === "manager") {
    return "Manager planning workspace";
  }

  return "Admin planning workspace";
});

const roleDescription = computed(() => {
  if (auth.role.value === "employee") {
    return "Review assignments, keep your schedule visible, and manage leave requests from one place.";
  }

  return "Move between tasks, planning, departments, schedules, and final assignments without leaving the main shell.";
});
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Workspace</p>
      <h3 class="page-title">{{ roleHeadline }}</h3>
      <p class="page-description">{{ roleDescription }}</p>
      <div class="pill-row">
        <span class="pill is-warm">{{ auth.user.value?.role || "No role" }}</span>
        <span class="pill">{{ auth.user.value?.employee_profile?.full_name || auth.user.value?.email || "No session" }}</span>
      </div>
    </section>

    <div class="grid-two">
      <SectionPlaceholder
        eyebrow="What you can do"
        title="Core daily flows"
        description="The shell now keeps the main operational routes close together instead of exposing backend contracts."
      >
        <ul class="resource-list">
          <li class="resource-item">
            <p class="resource-label">Tasks and requirements</p>
            <p class="resource-copy">Create, focus, and refine planning tasks in one connected flow.</p>
          </li>
          <li v-if="auth.role.value !== 'employee'" class="resource-item">
            <p class="resource-label">Planning and approvals</p>
            <p class="resource-copy">Launch runs, review proposals, and approve the selected assignment outcome.</p>
          </li>
          <li class="resource-item">
            <p class="resource-label">Departments and people</p>
            <p class="resource-copy">Browse department structure and open employee profiles where your role allows it.</p>
          </li>
        </ul>
      </SectionPlaceholder>

      <SectionPlaceholder
        eyebrow="Current profile"
        title="Session snapshot"
        description="A quick read-only view of who is currently signed in."
      >
        <ul class="key-value-list">
          <li class="key-value-item">
            <span class="key-label">Email</span>
            <span class="key-value">{{ auth.user.value?.email || "No authenticated user" }}</span>
          </li>
          <li class="key-value-item">
            <span class="key-label">Role</span>
            <span class="key-value">{{ auth.user.value?.role || "n/a" }}</span>
          </li>
          <li class="key-value-item">
            <span class="key-label">Employee profile</span>
            <span class="key-value">{{ auth.user.value?.employee_profile?.full_name || "Not linked" }}</span>
          </li>
        </ul>
      </SectionPlaceholder>
    </div>
  </div>
</template>
