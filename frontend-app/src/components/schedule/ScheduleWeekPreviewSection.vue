<script setup lang="ts">
import { computed } from "vue";

import type { SchedulePreviewDay, SchedulePreviewResponse } from "../../types/api";

const props = defineProps<{
  preview: SchedulePreviewResponse | null;
  isLoading: boolean;
  errorMessage: string;
  weekStart: string;
  title: string;
  description: string;
  emptyMessage: string;
}>();

const emit = defineEmits<{
  (event: "previous-week"): void;
  (event: "current-week"): void;
  (event: "next-week"): void;
  (event: "change-week-start", value: string): void;
}>();

const previewDays = computed(() => props.preview?.days ?? []);
const weekRangeLabel = computed(() => {
  if (!props.preview) {
    return "";
  }
  const formatter = new Intl.DateTimeFormat("en", { month: "short", day: "numeric" });
  return `${formatter.format(parseIsoDate(props.preview.week_start))} - ${formatter.format(parseIsoDate(props.preview.week_end))}`;
});

function parseIsoDate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day, 12, 0, 0);
}

function formatCalendarDate(value: string): string {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(parseIsoDate(value));
}

function formatTime(value: string | null): string {
  return value ? value.slice(0, 5) : "n/a";
}

function effectiveStatusLabel(day: SchedulePreviewDay): string {
  if (day.effective_day.source === "approved_leave") {
    return "Leave / non-working";
  }
  if (day.effective_day.source === "availability_override") {
    return day.effective_day.is_working_day ? "Override applied" : "Override / non-working";
  }
  if (day.effective_day.source === "no_rule") {
    return "No rule";
  }
  return day.effective_day.is_working_day ? "Working day" : "Off day";
}

function effectivePillClass(day: SchedulePreviewDay): string {
  if (day.effective_day.source === "approved_leave") {
    return "is-danger";
  }
  if (day.effective_day.source === "availability_override") {
    return day.effective_day.is_working_day ? "is-info" : "is-warm";
  }
  if (day.effective_day.source === "no_rule") {
    return "is-warm";
  }
  return day.effective_day.is_working_day ? "" : "is-warm";
}

function leaveTypeLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function onWeekStartChange(event: Event) {
  emit("change-week-start", (event.target as HTMLInputElement).value);
}
</script>

<template>
  <section class="records-card preview-section">
    <div class="editor-header preview-header">
      <div>
        <p class="section-caption">{{ title }}</p>
        <p class="resource-copy">{{ description }}</p>
      </div>
      <div class="inline-actions preview-actions">
        <label class="field-group preview-date-field">
          <span class="field-label">Week start</span>
          <input :value="weekStart" class="text-input" type="date" @input="onWeekStartChange" />
        </label>
        <button class="button-secondary" type="button" @click="emit('previous-week')">Previous week</button>
        <button class="button-secondary" type="button" @click="emit('current-week')">Current week</button>
        <button class="button-secondary" type="button" @click="emit('next-week')">Next week</button>
      </div>
    </div>

    <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="resource-copy">Loading effective weekly availability...</p>
    <div v-else-if="!preview" class="notice">{{ emptyMessage }}</div>
    <div v-else class="page-stack">
      <div class="pill-row">
        <span class="pill">{{ weekRangeLabel }}</span>
        <span class="pill">{{ preview.employee.full_name }}</span>
        <span v-if="preview.schedule" class="pill is-info">
          {{ preview.schedule.name }}{{ preview.schedule.is_default ? " · default" : "" }}
        </span>
      </div>

      <div class="preview-grid">
        <article v-for="day in previewDays" :key="day.date" class="resource-item preview-day-card">
          <div class="resource-heading">
            <div>
              <p class="resource-label">{{ day.weekday_label }}</p>
              <p class="item-meta">{{ formatCalendarDate(day.date) }}</p>
            </div>
            <span class="pill" :class="effectivePillClass(day)">
              {{ effectiveStatusLabel(day) }}
            </span>
          </div>

          <div class="pill-row">
            <span v-if="day.approved_leave" class="pill is-danger">Approved leave</span>
            <span v-if="day.availability_override" class="pill is-info">Availability override</span>
          </div>

          <p class="resource-copy">
            Effective:
            {{
              day.effective_day.is_working_day
                ? `${day.effective_day.capacity_hours}h`
                : "0h"
            }}
            <span v-if="day.effective_day.start_time || day.effective_day.end_time">
              · {{ formatTime(day.effective_day.start_time) }} → {{ formatTime(day.effective_day.end_time) }}
            </span>
          </p>

          <p v-if="day.approved_leave" class="resource-copy">
            Leave: {{ leaveTypeLabel(day.approved_leave.leave_type) }} · {{ day.approved_leave.start_date }} → {{ day.approved_leave.end_date }}
          </p>

          <p v-if="day.availability_override" class="resource-copy">
            Override: {{ day.availability_override.available_hours }}h{{ day.availability_override.reason ? ` · ${day.availability_override.reason}` : "" }}
          </p>

          <p v-if="day.base_rule" class="resource-copy muted-copy">
            Scheduled template:
            {{
              day.base_rule.is_working_day
                ? `${day.base_rule.capacity_hours}h`
                : "Off day"
            }}
            <span v-if="day.base_rule.start_time || day.base_rule.end_time">
              · {{ formatTime(day.base_rule.start_time) }} → {{ formatTime(day.base_rule.end_time) }}
            </span>
          </p>
          <p v-else class="resource-copy muted-copy">No weekly rule is stored for this weekday.</p>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.preview-section {
  gap: 1rem;
}

.preview-header {
  align-items: end;
}

.preview-actions {
  align-items: end;
  flex-wrap: wrap;
}

.preview-date-field {
  min-width: 11rem;
}

.preview-grid {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
}

.preview-day-card {
  gap: 0.6rem;
}

.muted-copy {
  color: var(--app-muted);
}

@media (max-width: 900px) {
  .preview-header {
    align-items: start;
  }

  .preview-actions {
    width: 100%;
  }
}
</style>
