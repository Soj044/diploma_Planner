<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import { useAuth } from "../../composables/useAuth";
import { coreService } from "../../services/core-service";
import { describeRequestError } from "../../services/http";
import type { WorkSchedule, WorkScheduleDay, WorkScheduleDayInput, WorkScheduleInput } from "../../types/api";

interface ScheduleFormState {
  name: string;
  is_default: boolean;
}

interface ScheduleDayFormState {
  weekday: string;
  is_working_day: boolean;
  capacity_hours: number;
  start_time: string;
  end_time: string;
}

const weekdayOptions = [
  { value: 0, label: "Monday" },
  { value: 1, label: "Tuesday" },
  { value: 2, label: "Wednesday" },
  { value: 3, label: "Thursday" },
  { value: 4, label: "Friday" },
  { value: 5, label: "Saturday" },
  { value: 6, label: "Sunday" },
] as const;

const auth = useAuth();
const schedules = ref<WorkSchedule[]>([]);
const scheduleDays = ref<WorkScheduleDay[]>([]);
const selectedScheduleId = ref<number | null>(null);
const editingScheduleId = ref<number | null>(null);
const editingDayId = ref<number | null>(null);
const isLoading = ref(false);
const isSavingSchedule = ref(false);
const isSavingDay = ref(false);
const deletingScheduleId = ref<number | null>(null);
const deletingDayId = ref<number | null>(null);
const errorMessage = ref("");
const successMessage = ref("");

const scheduleForm = reactive<ScheduleFormState>({
  name: "",
  is_default: true,
});

const dayForm = reactive<ScheduleDayFormState>({
  weekday: "0",
  is_working_day: true,
  capacity_hours: 8,
  start_time: "09:00",
  end_time: "18:00",
});

const weekdayLabelByValue = computed(() => {
  return new Map<number, string>(weekdayOptions.map((option) => [option.value, option.label]));
});

const selectedSchedule = computed(() => {
  return schedules.value.find((schedule) => schedule.id === selectedScheduleId.value) || null;
});

const filteredDays = computed(() => {
  if (selectedScheduleId.value === null) {
    return [];
  }

  return scheduleDays.value.filter((day) => day.schedule === selectedScheduleId.value);
});

const availableWeekdays = computed(() => {
  const reservedWeekdays = new Set(
    filteredDays.value
      .filter((day) => day.id !== editingDayId.value)
      .map((day) => day.weekday),
  );

  return weekdayOptions.filter((option) => !reservedWeekdays.has(option.value));
});

function resetMessages() {
  errorMessage.value = "";
  successMessage.value = "";
}

function resetScheduleForm() {
  scheduleForm.name = "";
  scheduleForm.is_default = true;
  editingScheduleId.value = null;
}

function resetDayForm() {
  dayForm.weekday = "0";
  dayForm.is_working_day = true;
  dayForm.capacity_hours = 8;
  dayForm.start_time = "09:00";
  dayForm.end_time = "18:00";
  editingDayId.value = null;
}

function selectSchedule(scheduleId: number | null) {
  selectedScheduleId.value = scheduleId;
  resetDayForm();
}

function startEditingSchedule(schedule: WorkSchedule) {
  editingScheduleId.value = schedule.id;
  scheduleForm.name = schedule.name;
  scheduleForm.is_default = schedule.is_default;
  selectSchedule(schedule.id);
  resetMessages();
}

function startEditingDay(day: WorkScheduleDay) {
  editingDayId.value = day.id;
  dayForm.weekday = String(day.weekday);
  dayForm.is_working_day = day.is_working_day;
  dayForm.capacity_hours = day.capacity_hours;
  dayForm.start_time = normalizeTimeInput(day.start_time);
  dayForm.end_time = normalizeTimeInput(day.end_time);
  resetMessages();
}

function normalizeTimeInput(value: string | null): string {
  return value ? value.slice(0, 5) : "";
}

function formatTime(value: string | null): string {
  return value ? value.slice(0, 5) : "None";
}

async function load() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    const [scheduleRows, dayRows] = await Promise.all([
      coreService.listWorkSchedules(),
      coreService.listWorkScheduleDays(),
    ]);

    schedules.value = scheduleRows;
    scheduleDays.value = dayRows;

    if (selectedScheduleId.value !== null && !scheduleRows.some((schedule) => schedule.id === selectedScheduleId.value)) {
      selectedScheduleId.value = scheduleRows[0]?.id ?? null;
    }

    if (selectedScheduleId.value === null && scheduleRows.length > 0) {
      selectedScheduleId.value = scheduleRows[0].id;
    }
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

function buildSchedulePayload(): WorkScheduleInput | null {
  if (auth.employeeId.value === null) {
    errorMessage.value = "Employee profile is required for self-service schedule management.";
    return null;
  }

  return {
    employee: auth.employeeId.value,
    name: scheduleForm.name.trim(),
    is_default: scheduleForm.is_default,
  };
}

function buildScheduleDayPayload(): WorkScheduleDayInput | null {
  if (selectedScheduleId.value === null) {
    errorMessage.value = "Select a schedule before editing schedule days.";
    return null;
  }

  if (!dayForm.is_working_day) {
    return {
      schedule: selectedScheduleId.value,
      weekday: Number(dayForm.weekday),
      is_working_day: false,
      capacity_hours: 0,
      start_time: null,
      end_time: null,
    };
  }

  if (dayForm.start_time && dayForm.end_time) {
    const startMinutes = toMinutes(dayForm.start_time);
    const endMinutes = toMinutes(dayForm.end_time);
    if (startMinutes === null || endMinutes === null) {
      errorMessage.value = "Start time and end time must be valid HH:MM values.";
      return null;
    }
    if (endMinutes <= startMinutes) {
      errorMessage.value = "End time must be later than start time.";
      return null;
    }
    const windowHours = (endMinutes - startMinutes) / 60;
    if (Number(dayForm.capacity_hours) > windowHours) {
      errorMessage.value = "Capacity hours cannot exceed the selected time window.";
      return null;
    }
  }

  return {
    schedule: selectedScheduleId.value,
    weekday: Number(dayForm.weekday),
    is_working_day: true,
    capacity_hours: Number(dayForm.capacity_hours),
    start_time: dayForm.start_time || null,
    end_time: dayForm.end_time || null,
  };
}

function toMinutes(value: string): number | null {
  const [hours, minutes] = value.split(":").map(Number);
  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) {
    return null;
  }
  return hours * 60 + minutes;
}

async function saveSchedule() {
  const payload = buildSchedulePayload();
  if (!payload) {
    return;
  }

  isSavingSchedule.value = true;
  resetMessages();

  try {
    const savedSchedule =
      editingScheduleId.value === null
        ? await coreService.createWorkSchedule(payload)
        : await coreService.updateWorkSchedule(editingScheduleId.value, payload);

    successMessage.value = editingScheduleId.value === null ? "Work schedule created." : "Work schedule updated.";
    resetScheduleForm();
    selectSchedule(savedSchedule.id);
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isSavingSchedule.value = false;
  }
}

async function removeSchedule(scheduleId: number) {
  deletingScheduleId.value = scheduleId;
  resetMessages();

  try {
    await coreService.deleteWorkSchedule(scheduleId);
    successMessage.value = "Work schedule deleted.";

    if (selectedScheduleId.value === scheduleId) {
      selectedScheduleId.value = null;
    }

    if (editingScheduleId.value === scheduleId) {
      resetScheduleForm();
    }

    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    deletingScheduleId.value = null;
  }
}

async function saveScheduleDay() {
  const payload = buildScheduleDayPayload();
  if (!payload) {
    return;
  }

  isSavingDay.value = true;
  resetMessages();

  try {
    await (editingDayId.value === null
      ? coreService.createWorkScheduleDay(payload)
      : coreService.updateWorkScheduleDay(editingDayId.value, payload));

    successMessage.value = editingDayId.value === null ? "Schedule day created." : "Schedule day updated.";
    resetDayForm();
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isSavingDay.value = false;
  }
}

async function removeScheduleDay(dayId: number) {
  deletingDayId.value = dayId;
  resetMessages();

  try {
    await coreService.deleteWorkScheduleDay(dayId);
    successMessage.value = "Schedule day deleted.";
    if (editingDayId.value === dayId) {
      resetDayForm();
    }
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    deletingDayId.value = null;
  }
}

onMounted(async () => {
  await load();
  resetScheduleForm();
  resetDayForm();
});
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Employee self-service</p>
      <h3 class="page-title">Own work schedules and weekdays</h3>
      <p class="page-description">
        Manage your own work schedule templates and weekday rules from one place.
      </p>
    </section>

    <div v-if="auth.employeeId.value === null" class="notice">
      Employee profile is missing, so self-service schedules cannot be edited from this account.
    </div>

    <div v-else class="page-stack">
      <section class="page-card">
        <div class="data-layout">
          <form class="editor-card" @submit.prevent="saveSchedule">
            <div class="editor-header">
              <div>
                <p class="section-caption">
                  {{ editingScheduleId === null ? "Create work schedule" : "Edit work schedule" }}
                </p>
                <p class="resource-copy">Create a reusable schedule and then add weekday rules for it below.</p>
              </div>
              <div class="inline-actions">
                <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
                <button
                  v-if="editingScheduleId !== null"
                  class="button-secondary"
                  type="button"
                  :disabled="isSavingSchedule"
                  @click="resetScheduleForm"
                >
                  Cancel edit
                </button>
              </div>
            </div>

            <div class="form-grid">
              <label class="field-group field-group-span-2">
                <span class="field-label">Name</span>
                <input v-model.trim="scheduleForm.name" class="text-input" required />
              </label>

              <label class="field-group field-group-span-2 checkbox-row">
                <input v-model="scheduleForm.is_default" class="check-input" type="checkbox" />
                <span class="field-label">Default schedule</span>
              </label>
            </div>

            <div class="action-row">
              <button class="button-primary" type="submit" :disabled="isSavingSchedule">
                {{ isSavingSchedule ? "Saving..." : editingScheduleId === null ? "Create schedule" : "Save schedule" }}
              </button>
            </div>
          </form>

          <div class="records-card">
            <div class="editor-header">
              <div>
                <p class="section-caption">Existing schedules</p>
                <p class="resource-copy">Select one schedule to edit its weekday rules.</p>
              </div>
              <span class="pill">{{ schedules.length }} rows</span>
            </div>

            <p v-if="isLoading" class="resource-copy">Loading...</p>
            <p v-else-if="schedules.length === 0" class="empty-state">No work schedules yet.</p>
            <ul v-else class="resource-list">
              <li
                v-for="schedule in schedules"
                :key="schedule.id"
                class="resource-item"
                :class="{ 'resource-item-active': selectedScheduleId === schedule.id }"
              >
                <div class="resource-heading">
                  <p class="resource-label">{{ schedule.name }}</p>
                  <div class="inline-actions">
                    <button class="button-secondary" type="button" @click="selectSchedule(schedule.id)">Days</button>
                    <button class="button-secondary" type="button" @click="startEditingSchedule(schedule)">Edit</button>
                    <button
                      class="button-danger"
                      type="button"
                      :disabled="deletingScheduleId === schedule.id"
                      @click="removeSchedule(schedule.id)"
                    >
                      {{ deletingScheduleId === schedule.id ? "Deleting..." : "Delete" }}
                    </button>
                  </div>
                </div>
                <div class="pill-row">
                  <span class="pill">{{ schedule.is_default ? "default" : "custom" }}</span>
                </div>
                <p class="item-meta">ID {{ schedule.id }} · updated {{ new Date(schedule.updated_at).toLocaleString() }}</p>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section class="page-card">
        <div class="data-layout" :class="{ 'data-layout-single': selectedScheduleId === null }">
          <form v-if="selectedScheduleId !== null" class="editor-card" @submit.prevent="saveScheduleDay">
            <div class="editor-header">
              <div>
                <p class="section-caption">
                  {{ editingDayId === null ? "Create schedule day" : "Edit schedule day" }}
                </p>
                <p class="resource-copy">Add the weekday hours that belong to the schedule currently in focus.</p>
              </div>
              <div class="inline-actions">
                <button
                  v-if="editingDayId !== null"
                  class="button-secondary"
                  type="button"
                  :disabled="isSavingDay"
                  @click="resetDayForm"
                >
                  Cancel edit
                </button>
              </div>
            </div>

            <div class="form-grid">
              <label class="field-group">
                <span class="field-label">Weekday</span>
                <select v-model="dayForm.weekday" class="select-input" required>
                  <option v-for="option in availableWeekdays" :key="option.value" :value="String(option.value)">
                    {{ option.label }}
                  </option>
                  <option
                    v-if="
                      editingDayId !== null &&
                      !availableWeekdays.some((option) => String(option.value) === dayForm.weekday)
                    "
                    :value="dayForm.weekday"
                  >
                    {{ weekdayLabelByValue.get(Number(dayForm.weekday)) }}
                  </option>
                </select>
              </label>

              <label class="field-group">
                <span class="field-label">Capacity hours</span>
                <input v-model.number="dayForm.capacity_hours" class="text-input" min="0" max="24" type="number" required />
              </label>

              <label class="field-group">
                <span class="field-label">Start time</span>
                <input v-model="dayForm.start_time" class="text-input" type="time" />
              </label>

              <label class="field-group">
                <span class="field-label">End time</span>
                <input v-model="dayForm.end_time" class="text-input" type="time" />
              </label>

              <label class="field-group field-group-span-2 checkbox-row">
                <input v-model="dayForm.is_working_day" class="check-input" type="checkbox" />
                <span class="field-label">Working day</span>
              </label>
            </div>

            <div class="action-row">
              <button class="button-primary" type="submit" :disabled="isSavingDay">
                {{ isSavingDay ? "Saving..." : editingDayId === null ? "Create day" : "Save day" }}
              </button>
            </div>
          </form>

          <div class="records-card">
            <div class="editor-header">
              <div>
                <p class="section-caption">
                  {{ selectedSchedule ? `Weekday rules for ${selectedSchedule.name}` : "Weekday rules" }}
                </p>
                <p class="resource-copy">
                  {{ selectedSchedule ? "This list is filtered to the currently selected schedule." : "Select a schedule first." }}
                </p>
              </div>
              <span class="pill">{{ filteredDays.length }} rows</span>
            </div>

            <div v-if="selectedScheduleId === null" class="notice">
              Create or select a work schedule before adding weekday rules.
            </div>
            <p v-else-if="isLoading" class="resource-copy">Loading...</p>
            <p v-else-if="filteredDays.length === 0" class="empty-state">No weekday rules yet.</p>
            <ul v-else class="resource-list">
              <li v-for="day in filteredDays" :key="day.id" class="resource-item">
                <div class="resource-heading">
                  <p class="resource-label">{{ weekdayLabelByValue.get(day.weekday) }}</p>
                  <div class="inline-actions">
                    <button class="button-secondary" type="button" @click="startEditingDay(day)">Edit</button>
                    <button
                      class="button-danger"
                      type="button"
                      :disabled="deletingDayId === day.id"
                      @click="removeScheduleDay(day.id)"
                    >
                      {{ deletingDayId === day.id ? "Deleting..." : "Delete" }}
                    </button>
                  </div>
                </div>
                <div class="pill-row">
                  <span class="pill">{{ day.is_working_day ? "working" : "off" }}</span>
                  <span class="pill is-warm">{{ day.capacity_hours }}h</span>
                </div>
                <p class="resource-copy">
                  Time window: {{ formatTime(day.start_time) }} - {{ formatTime(day.end_time) }}
                </p>
                <p class="item-meta">Day ID {{ day.id }}</p>
              </li>
            </ul>
          </div>
        </div>

        <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
        <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>
      </section>
    </div>
  </div>
</template>
