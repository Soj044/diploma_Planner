<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { useAuth } from "../composables/useAuth";
import { coreService } from "../services/core-service";
import { describeRequestError } from "../services/http";
import type { WorkSchedule, WorkScheduleDay } from "../types/api";

const weekdayLabels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const auth = useAuth();
const schedules = ref<WorkSchedule[]>([]);
const scheduleDays = ref<WorkScheduleDay[]>([]);
const isLoading = ref(false);
const errorMessage = ref("");

const orderedSchedules = computed(() => {
  return [...schedules.value].sort((left, right) => {
    if (left.is_default !== right.is_default) {
      return left.is_default ? -1 : 1;
    }

    return left.name.localeCompare(right.name);
  });
});

const daysByScheduleId = computed(() => {
  return new Map(
    orderedSchedules.value.map((schedule) => {
      const days = scheduleDays.value
        .filter((day) => day.schedule === schedule.id)
        .sort((left, right) => left.weekday - right.weekday);
      return [schedule.id, days];
    }),
  );
});

function findScheduleDay(scheduleId: number, weekday: number) {
  return daysByScheduleId.value.get(scheduleId)?.find((day) => day.weekday === weekday) || null;
}

async function load() {
  if (auth.role.value !== "employee") {
    return;
  }

  isLoading.value = true;
  errorMessage.value = "";

  try {
    const [scheduleRows, dayRows] = await Promise.all([
      coreService.listWorkSchedules(),
      coreService.listWorkScheduleDays(),
    ]);
    schedules.value = scheduleRows;
    scheduleDays.value = dayRows;
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
      <p class="eyebrow">Schedule</p>
      <h3 class="page-title">
        {{ auth.role.value === "employee" ? "Your weekly work schedule" : "Schedule workspace" }}
      </h3>
      <p class="page-description">
        {{
          auth.role.value === "employee"
            ? "Employee schedule visibility is now read-only and stays aligned with backend self-scope rules."
            : "Manager/admin scheduling tools stay deferred in this slice. The canonical route remains in place for the next stage."
        }}
      </p>
      <div class="pill-row">
        <span class="pill">/schedule</span>
        <span class="pill is-warm">{{ auth.role.value ?? "unknown role" }}</span>
      </div>
    </section>

    <section v-if="auth.role.value === 'employee'" class="page-card">
      <div class="editor-header">
        <div>
          <p class="section-caption">Read-only schedules</p>
          <p class="resource-copy">The browser no longer exposes employee schedule create, edit, or delete controls.</p>
        </div>
        <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
      </div>

      <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
      <p v-else-if="isLoading" class="resource-copy">Loading schedules and weekdays...</p>
      <p v-else-if="orderedSchedules.length === 0" class="empty-state">No schedules are available for this employee.</p>
      <div v-else class="page-stack">
        <section v-for="schedule in orderedSchedules" :key="schedule.id" class="records-card">
          <div class="editor-header">
            <div>
              <p class="section-caption">
                {{ schedule.name }}
                <span v-if="schedule.is_default" class="pill">Default</span>
              </p>
              <p class="resource-copy">Schedule #{{ schedule.id }}</p>
            </div>
          </div>

          <ul class="resource-list">
            <li
              v-for="weekday in weekdayLabels.map((label, index) => ({ label, index }))"
              :key="`${schedule.id}-${weekday.index}`"
              class="resource-item"
            >
              <template v-if="findScheduleDay(schedule.id, weekday.index)">
                <div class="resource-heading">
                  <p class="resource-label">{{ weekday.label }}</p>
                  <span class="pill" :class="{ 'is-warm': !findScheduleDay(schedule.id, weekday.index)?.is_working_day }">
                    {{ findScheduleDay(schedule.id, weekday.index)?.is_working_day ? "Working day" : "Off day" }}
                  </span>
                </div>
                <p class="resource-copy">
                  Capacity: {{ findScheduleDay(schedule.id, weekday.index)?.capacity_hours }}h
                  <span
                    v-if="findScheduleDay(schedule.id, weekday.index)?.start_time || findScheduleDay(schedule.id, weekday.index)?.end_time"
                  >
                    · {{ findScheduleDay(schedule.id, weekday.index)?.start_time?.slice(0, 5) || "n/a" }} →
                    {{ findScheduleDay(schedule.id, weekday.index)?.end_time?.slice(0, 5) || "n/a" }}
                  </span>
                </p>
              </template>
              <template v-else>
                <div class="resource-heading">
                  <p class="resource-label">{{ weekday.label }}</p>
                  <span class="pill is-warm">No rule</span>
                </div>
                <p class="resource-copy">No schedule rule is stored for this weekday.</p>
              </template>
            </li>
          </ul>
        </section>
      </div>
    </section>

    <SectionPlaceholder
      v-else
      eyebrow="Canonical route"
      title="Manager/admin scheduling remains a follow-up slice"
      description="This route stays stable while the dedicated management UI for cross-employee schedules lands in a later stage."
    >
      <div class="notice">
        Keep scheduling business truth in `core-service`. This slice only finalizes employee read-only visibility.
      </div>
    </SectionPlaceholder>
  </div>
</template>
