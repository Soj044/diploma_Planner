<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";

import DialogModal from "../components/DialogModal.vue";
import ScheduleWeekPreviewSection from "../components/schedule/ScheduleWeekPreviewSection.vue";
import { useAuth } from "../composables/useAuth";
import { coreService } from "../services/core-service";
import { describeRequestError } from "../services/http";
import type {
  Employee,
  SchedulePreviewResponse,
  WorkSchedule,
  WorkScheduleDay,
  WorkScheduleDayInput,
  WorkScheduleInput,
} from "../types/api";

interface ScheduleFormState {
  employee: string;
  name: string;
  is_default: boolean;
}

interface ScheduleDayFormState {
  weekday: number;
  is_working_day: boolean;
  capacity_hours: number;
  start_time: string;
  end_time: string;
}

const weekdayLabels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const auth = useAuth();

const employees = ref<Employee[]>([]);
const schedules = ref<WorkSchedule[]>([]);
const scheduleDays = ref<WorkScheduleDay[]>([]);
const selectedEmployeeId = ref("");
const selectedScheduleId = ref("");
const isLoading = ref(false);
const isPreviewLoading = ref(false);
const isSavingSchedule = ref(false);
const isSavingDay = ref(false);
const deletingScheduleId = ref<number | null>(null);
const deletingDayId = ref<number | null>(null);
const editingScheduleId = ref<number | null>(null);
const editingScheduleDayId = ref<number | null>(null);
const errorMessage = ref("");
const successMessage = ref("");
const previewErrorMessage = ref("");
const isScheduleModalOpen = ref(false);
const isDayModalOpen = ref(false);
const schedulePreview = ref<SchedulePreviewResponse | null>(null);
const previewWeekStart = ref(currentWeekStart());

const scheduleForm = reactive<ScheduleFormState>({
  employee: "",
  name: "",
  is_default: false,
});

const dayForm = reactive<ScheduleDayFormState>({
  weekday: 0,
  is_working_day: true,
  capacity_hours: 8,
  start_time: "09:00",
  end_time: "18:00",
});

const orderedEmployees = computed(() => {
  return [...employees.value].sort((left, right) => {
    if (left.is_active !== right.is_active) {
      return left.is_active ? -1 : 1;
    }
    return left.full_name.localeCompare(right.full_name);
  });
});

const selectedEmployee = computed(() => {
  return employees.value.find((employee) => String(employee.id) === selectedEmployeeId.value) ?? null;
});

const employeeSchedules = computed(() => {
  if (!selectedEmployeeId.value) {
    return [];
  }

  return schedules.value
    .filter((schedule) => String(schedule.employee) === selectedEmployeeId.value)
    .sort((left, right) => {
      if (left.is_default !== right.is_default) {
        return left.is_default ? -1 : 1;
      }
      return left.name.localeCompare(right.name);
    });
});

const selectedSchedule = computed(() => {
  return employeeSchedules.value.find((schedule) => String(schedule.id) === selectedScheduleId.value) ?? null;
});

const previewEmployeeId = computed(() => {
  if (auth.role.value === "employee") {
    return auth.employeeId.value;
  }
  return selectedEmployeeId.value ? Number(selectedEmployeeId.value) : null;
});

const schedulePreviewTitle = computed(() => {
  return auth.role.value === "employee" ? "Effective weekly calendar" : "Effective weekly calendar preview";
});

const schedulePreviewDescription = computed(() => {
  return auth.role.value === "employee"
    ? "Real dates, approved leave, and availability overrides are applied on top of the schedule you focus below."
    : "Preview how the selected schedule behaves on real dates once approved leave and date-level overrides are applied.";
});

const schedulePreviewEmptyMessage = computed(() => {
  return selectedSchedule.value
    ? "Choose a week to inspect the effective calendar preview."
    : "Select a schedule first to inspect the effective weekly calendar.";
});

const daysByScheduleId = computed(() => {
  return new Map(
    schedules.value.map((schedule) => {
      const days = scheduleDays.value
        .filter((day) => day.schedule === schedule.id)
        .sort((left, right) => left.weekday - right.weekday);
      return [schedule.id, days];
    }),
  );
});

const selectedScheduleWeekdays = computed(() => {
  const currentSchedule = selectedSchedule.value;
  if (!currentSchedule) {
    return [];
  }

  const rules = daysByScheduleId.value.get(currentSchedule.id) ?? [];
  return weekdayLabels.map((label, weekday) => {
    const rule = rules.find((day) => day.weekday === weekday) ?? null;
    return {
      weekday,
      label,
      rule,
    };
  });
});

function parseIsoDate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day, 12, 0, 0);
}

function formatIsoDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function currentWeekStart(): string {
  const today = new Date();
  const monday = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 12, 0, 0);
  const weekdayOffset = (monday.getDay() + 6) % 7;
  monday.setDate(monday.getDate() - weekdayOffset);
  return formatIsoDate(monday);
}

function shiftPreviewWeek(days: number) {
  const next = parseIsoDate(previewWeekStart.value);
  next.setDate(next.getDate() + days);
  previewWeekStart.value = formatIsoDate(next);
}

function resetScheduleForm() {
  editingScheduleId.value = null;
  scheduleForm.employee = selectedEmployeeId.value;
  scheduleForm.name = "";
  scheduleForm.is_default = false;
}

function resetDayForm() {
  editingScheduleDayId.value = null;
  dayForm.weekday = 0;
  dayForm.is_working_day = true;
  dayForm.capacity_hours = 8;
  dayForm.start_time = "09:00";
  dayForm.end_time = "18:00";
}

function openCreateScheduleModal() {
  resetScheduleForm();
  errorMessage.value = "";
  successMessage.value = "";
  isScheduleModalOpen.value = true;
}

function openEditScheduleModal(schedule: WorkSchedule) {
  editingScheduleId.value = schedule.id;
  scheduleForm.employee = String(schedule.employee);
  scheduleForm.name = schedule.name;
  scheduleForm.is_default = schedule.is_default;
  errorMessage.value = "";
  successMessage.value = "";
  isScheduleModalOpen.value = true;
}

function openCreateDayModal(weekday: number) {
  resetDayForm();
  dayForm.weekday = weekday;
  errorMessage.value = "";
  successMessage.value = "";
  isDayModalOpen.value = true;
}

function openEditDayModal(day: WorkScheduleDay) {
  editingScheduleDayId.value = day.id;
  dayForm.weekday = day.weekday;
  dayForm.is_working_day = day.is_working_day;
  dayForm.capacity_hours = day.capacity_hours;
  dayForm.start_time = day.start_time?.slice(0, 5) || "";
  dayForm.end_time = day.end_time?.slice(0, 5) || "";
  errorMessage.value = "";
  successMessage.value = "";
  isDayModalOpen.value = true;
}

function buildSchedulePayload(): WorkScheduleInput | null {
  if (!scheduleForm.employee) {
    errorMessage.value = "Employee is required for a schedule.";
    return null;
  }

  return {
    employee: Number(scheduleForm.employee),
    name: scheduleForm.name.trim(),
    is_default: scheduleForm.is_default,
  };
}

function buildDayPayload(): WorkScheduleDayInput | null {
  if (!selectedSchedule.value) {
    errorMessage.value = "Select a schedule before editing weekday rules.";
    return null;
  }

  if (!dayForm.is_working_day) {
    return {
      schedule: selectedSchedule.value.id,
      weekday: dayForm.weekday,
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
    schedule: selectedSchedule.value.id,
    weekday: dayForm.weekday,
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

function syncSelectionAfterLoad() {
  if (auth.role.value === "employee") {
    selectedEmployeeId.value = auth.employeeId.value ? String(auth.employeeId.value) : "";
    const availableSchedules = employeeSchedules.value;
    if (!availableSchedules.some((schedule) => String(schedule.id) === selectedScheduleId.value)) {
      selectedScheduleId.value = availableSchedules[0] ? String(availableSchedules[0].id) : "";
    }
    return;
  }

  const availableEmployees = orderedEmployees.value;
  if (!availableEmployees.some((employee) => String(employee.id) === selectedEmployeeId.value)) {
    selectedEmployeeId.value = availableEmployees[0] ? String(availableEmployees[0].id) : "";
  }

  const availableSchedules = employeeSchedules.value;
  if (!availableSchedules.some((schedule) => String(schedule.id) === selectedScheduleId.value)) {
    selectedScheduleId.value = availableSchedules[0] ? String(availableSchedules[0].id) : "";
  }
}

async function loadSchedulePreview() {
  const employeeId = previewEmployeeId.value;
  if (!employeeId || !selectedSchedule.value) {
    schedulePreview.value = null;
    previewErrorMessage.value = "";
    return;
  }

  isPreviewLoading.value = true;
  previewErrorMessage.value = "";

  try {
    schedulePreview.value = await coreService.getSchedulePreview(
      employeeId,
      previewWeekStart.value,
      selectedSchedule.value.id,
    );
  } catch (error: unknown) {
    schedulePreview.value = null;
    previewErrorMessage.value = describeRequestError(error);
  } finally {
    isPreviewLoading.value = false;
  }
}

async function load() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    if (auth.role.value === "employee") {
      const [scheduleRows, dayRows] = await Promise.all([
        coreService.listWorkSchedules(),
        coreService.listWorkScheduleDays(),
      ]);
      schedules.value = scheduleRows;
      scheduleDays.value = dayRows;
      employees.value = [];
      syncSelectionAfterLoad();
      await loadSchedulePreview();
      return;
    }

    const [employeeRows, scheduleRows, dayRows] = await Promise.all([
      coreService.listEmployees(),
      coreService.listWorkSchedules(),
      coreService.listWorkScheduleDays(),
    ]);
    employees.value = employeeRows;
    schedules.value = scheduleRows;
    scheduleDays.value = dayRows;
    syncSelectionAfterLoad();
    await loadSchedulePreview();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

async function saveSchedule() {
  const payload = buildSchedulePayload();
  if (!payload) {
    return;
  }

  isSavingSchedule.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const savedSchedule =
      editingScheduleId.value === null
        ? await coreService.createWorkSchedule(payload)
        : await coreService.updateWorkSchedule(editingScheduleId.value, payload);
    selectedEmployeeId.value = String(savedSchedule.employee);
    selectedScheduleId.value = String(savedSchedule.id);
    successMessage.value = editingScheduleId.value === null ? "Schedule created." : "Schedule updated.";
    isScheduleModalOpen.value = false;
    resetScheduleForm();
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isSavingSchedule.value = false;
  }
}

async function saveScheduleDay() {
  const payload = buildDayPayload();
  if (!payload) {
    return;
  }

  isSavingDay.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    await (editingScheduleDayId.value === null
      ? coreService.createWorkScheduleDay(payload)
      : coreService.updateWorkScheduleDay(editingScheduleDayId.value, payload));
    successMessage.value = editingScheduleDayId.value === null ? "Weekday rule created." : "Weekday rule updated.";
    isDayModalOpen.value = false;
    resetDayForm();
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isSavingDay.value = false;
  }
}

async function removeSchedule(schedule: WorkSchedule) {
  if (!window.confirm(`Delete schedule “${schedule.name}”?`)) {
    return;
  }

  deletingScheduleId.value = schedule.id;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    await coreService.deleteWorkSchedule(schedule.id);
    successMessage.value = "Schedule deleted.";
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    deletingScheduleId.value = null;
  }
}

async function removeScheduleDay(day: WorkScheduleDay) {
  if (!window.confirm(`Delete the ${weekdayLabels[day.weekday]} rule?`)) {
    return;
  }

  deletingDayId.value = day.id;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    await coreService.deleteWorkScheduleDay(day.id);
    successMessage.value = "Weekday rule deleted.";
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    deletingDayId.value = null;
  }
}

watch(orderedEmployees, () => {
  syncSelectionAfterLoad();
});

watch(employeeSchedules, () => {
  syncSelectionAfterLoad();
});

watch(selectedEmployeeId, (employeeId) => {
  if (!employeeId) {
    selectedScheduleId.value = "";
    return;
  }

  if (!scheduleForm.employee) {
    scheduleForm.employee = employeeId;
  }
});

watch([selectedEmployeeId, selectedScheduleId, previewWeekStart], () => {
  void loadSchedulePreview();
});

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
            ? "Review your schedule templates together with a real weekly calendar that applies approved leave and date-level overrides."
            : "Managers and admins can manage weekly schedules for any employee and preview how they behave on real calendar dates."
        }}
      </p>
      <div class="pill-row">
        <span class="pill is-warm">{{ auth.role.value ?? "unknown role" }}</span>
      </div>
    </section>

    <section v-if="auth.role.value === 'employee'" class="page-card">
      <div class="editor-header">
        <div>
          <p class="section-caption">Read-only schedules</p>
          <p class="resource-copy">Focus one schedule template to compare its weekly rules with real dates, leave, and overrides.</p>
        </div>
        <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
      </div>

      <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
      <p v-else-if="isLoading" class="resource-copy">Loading schedules and weekdays...</p>
      <p v-else-if="employeeSchedules.length === 0" class="empty-state">No schedules are available for this employee.</p>
      <div v-else class="grid-two">
        <section class="records-card">
          <div class="editor-header">
            <div>
              <p class="section-caption">Your schedule templates</p>
              <p class="resource-copy">Choose one template to inspect its stored weekday rules and the effective weekly calendar.</p>
            </div>
            <span class="pill">{{ employeeSchedules.length }} schedules</span>
          </div>

          <ul class="resource-list">
            <li
              v-for="schedule in employeeSchedules"
              :key="schedule.id"
              class="resource-item"
              :class="{ 'is-selected': String(schedule.id) === selectedScheduleId }"
            >
              <div class="resource-heading">
                <div>
                  <p class="resource-label">{{ schedule.name }}</p>
                  <p class="resource-copy">
                    Schedule #{{ schedule.id }}
                    <span v-if="schedule.is_default">· default</span>
                  </p>
                </div>
                <button class="button-secondary" type="button" @click="selectedScheduleId = String(schedule.id)">
                  {{ String(schedule.id) === selectedScheduleId ? "Selected" : "Open" }}
                </button>
              </div>
            </li>
          </ul>
        </section>

        <div class="page-stack">
          <section class="records-card">
            <div class="editor-header">
              <div>
                <p class="section-caption">
                  {{ selectedSchedule ? `${selectedSchedule.name} weekdays` : "Weekday rules" }}
                </p>
                <p class="resource-copy">
                  {{
                    selectedSchedule
                      ? "Stored weekly rules for the selected schedule template."
                      : "Select a schedule to inspect its weekday rules."
                  }}
                </p>
              </div>
              <span v-if="selectedSchedule?.is_default" class="pill">Default schedule</span>
            </div>

            <p v-if="!selectedSchedule" class="empty-state">Select a schedule to inspect weekday rules.</p>
            <ul v-else class="resource-list">
              <li v-for="entry in selectedScheduleWeekdays" :key="entry.weekday" class="resource-item">
                <div class="resource-heading">
                  <div>
                    <p class="resource-label">{{ entry.label }}</p>
                    <p class="resource-copy">
                      {{
                        entry.rule
                          ? entry.rule.is_working_day
                            ? `Capacity ${entry.rule.capacity_hours}h`
                            : "Off day"
                          : "No rule yet"
                      }}
                      <span v-if="entry.rule && (entry.rule.start_time || entry.rule.end_time)">
                        · {{ entry.rule.start_time?.slice(0, 5) || "n/a" }} → {{ entry.rule.end_time?.slice(0, 5) || "n/a" }}
                      </span>
                    </p>
                  </div>
                </div>
              </li>
            </ul>
          </section>

          <ScheduleWeekPreviewSection
            :preview="schedulePreview"
            :is-loading="isPreviewLoading"
            :error-message="previewErrorMessage"
            :week-start="previewWeekStart"
            :title="schedulePreviewTitle"
            :description="schedulePreviewDescription"
            :empty-message="schedulePreviewEmptyMessage"
            @previous-week="shiftPreviewWeek(-7)"
            @current-week="previewWeekStart = currentWeekStart()"
            @next-week="shiftPreviewWeek(7)"
            @change-week-start="previewWeekStart = $event"
          />
        </div>
      </div>
    </section>

    <template v-else>
      <section class="page-card">
        <div class="editor-header">
          <div>
            <p class="section-caption">Employee schedule selection</p>
            <p class="resource-copy">
              Choose an employee to manage reusable weekly schedules and weekday-level availability rules.
            </p>
          </div>
          <div class="inline-actions">
            <button class="button-primary" type="button" :disabled="!selectedEmployeeId" @click="openCreateScheduleModal">
              Create schedule
            </button>
            <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
          </div>
        </div>

        <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
        <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>
        <p v-if="isLoading" class="resource-copy">Loading employees, schedules, and weekday rules...</p>

        <div v-else class="page-stack">
          <label class="field-group">
            <span class="field-label">Employee</span>
            <select v-model="selectedEmployeeId" class="select-input">
              <option v-if="orderedEmployees.length === 0" value="">No employees available</option>
              <option v-for="employee in orderedEmployees" :key="employee.id" :value="String(employee.id)">
                {{ employee.full_name }} · {{ employee.position_name || "No position" }}
                {{ employee.is_active ? "" : " · inactive" }}
              </option>
            </select>
          </label>

          <p v-if="!selectedEmployee" class="empty-state">Select an employee to inspect schedules.</p>
          <div v-else class="grid-two">
            <section class="records-card">
              <div class="editor-header">
                <div>
                  <p class="section-caption">{{ selectedEmployee.full_name }}</p>
                  <p class="resource-copy">
                    {{ selectedEmployee.position_name || "No position" }} ·
                    {{ selectedEmployee.is_active ? "active employee" : "inactive employee" }}
                  </p>
                </div>
                <span class="pill">{{ employeeSchedules.length }} schedules</span>
              </div>

              <p v-if="employeeSchedules.length === 0" class="empty-state">
                No schedules exist for this employee yet.
              </p>
              <ul v-else class="resource-list">
                <li
                  v-for="schedule in employeeSchedules"
                  :key="schedule.id"
                  class="resource-item"
                  :class="{ 'is-selected': String(schedule.id) === selectedScheduleId }"
                >
                  <div class="resource-heading">
                    <div>
                      <p class="resource-label">{{ schedule.name }}</p>
                      <p class="resource-copy">
                        Schedule #{{ schedule.id }}
                        <span v-if="schedule.is_default">· default</span>
                      </p>
                    </div>
                    <div class="inline-actions">
                      <button class="button-secondary" type="button" @click="selectedScheduleId = String(schedule.id)">
                        {{ String(schedule.id) === selectedScheduleId ? "Selected" : "Open" }}
                      </button>
                      <button class="button-secondary" type="button" @click="openEditScheduleModal(schedule)">Edit</button>
                      <button
                        class="button-danger"
                        type="button"
                        :disabled="deletingScheduleId === schedule.id"
                        @click="removeSchedule(schedule)"
                      >
                        {{ deletingScheduleId === schedule.id ? "Deleting..." : "Delete" }}
                      </button>
                    </div>
                  </div>
                </li>
              </ul>
            </section>

            <div class="page-stack">
              <section class="records-card">
                <div class="editor-header">
                  <div>
                    <p class="section-caption">
                      {{ selectedSchedule ? `${selectedSchedule.name} weekdays` : "Weekday rules" }}
                    </p>
                    <p class="resource-copy">
                      {{
                        selectedSchedule
                          ? "Add or update weekday rules for the selected schedule."
                          : "Choose a schedule to manage day-level capacity and working hours."
                      }}
                    </p>
                  </div>
                  <span v-if="selectedSchedule?.is_default" class="pill">Default schedule</span>
                </div>

                <p v-if="!selectedSchedule" class="empty-state">Select a schedule to manage weekday rules.</p>
                <ul v-else class="resource-list">
                  <li v-for="entry in selectedScheduleWeekdays" :key="entry.weekday" class="resource-item">
                    <div class="resource-heading">
                      <div>
                        <p class="resource-label">{{ entry.label }}</p>
                        <p class="resource-copy">
                          {{
                            entry.rule
                              ? entry.rule.is_working_day
                                ? `Capacity ${entry.rule.capacity_hours}h`
                                : "Off day"
                              : "No rule yet"
                          }}
                          <span v-if="entry.rule && (entry.rule.start_time || entry.rule.end_time)">
                            · {{ entry.rule.start_time?.slice(0, 5) || "n/a" }} → {{ entry.rule.end_time?.slice(0, 5) || "n/a" }}
                          </span>
                        </p>
                      </div>
                      <div class="inline-actions">
                        <button
                          v-if="entry.rule"
                          class="button-secondary"
                          type="button"
                          @click="openEditDayModal(entry.rule)"
                        >
                          Edit
                        </button>
                        <button
                          v-else
                          class="button-secondary"
                          type="button"
                          @click="openCreateDayModal(entry.weekday)"
                        >
                          Add rule
                        </button>
                        <button
                          v-if="entry.rule"
                          class="button-danger"
                          type="button"
                          :disabled="deletingDayId === entry.rule.id"
                          @click="removeScheduleDay(entry.rule)"
                        >
                          {{ deletingDayId === entry.rule.id ? "Deleting..." : "Delete" }}
                        </button>
                      </div>
                    </div>
                  </li>
                </ul>
              </section>

              <ScheduleWeekPreviewSection
                :preview="schedulePreview"
                :is-loading="isPreviewLoading"
                :error-message="previewErrorMessage"
                :week-start="previewWeekStart"
                :title="schedulePreviewTitle"
                :description="schedulePreviewDescription"
                :empty-message="schedulePreviewEmptyMessage"
                @previous-week="shiftPreviewWeek(-7)"
                @current-week="previewWeekStart = currentWeekStart()"
                @next-week="shiftPreviewWeek(7)"
                @change-week-start="previewWeekStart = $event"
              />
            </div>
          </div>
        </div>
      </section>
    </template>

    <DialogModal
      :open="isScheduleModalOpen"
      :title="editingScheduleId === null ? 'Create schedule' : 'Edit schedule'"
      description="Set up a reusable weekly schedule template for the selected employee."
      @close="isScheduleModalOpen = false"
    >
      <form class="page-stack" @submit.prevent="saveSchedule">
        <div class="form-grid">
          <label class="field-group">
            <span class="field-label">Employee</span>
            <select v-model="scheduleForm.employee" class="select-input" required>
              <option value="" disabled>Select employee</option>
              <option v-for="employee in orderedEmployees" :key="employee.id" :value="String(employee.id)">
                {{ employee.full_name }}
              </option>
            </select>
          </label>

          <label class="field-group">
            <span class="field-label">Schedule name</span>
            <input v-model.trim="scheduleForm.name" class="text-input" type="text" required />
          </label>

          <label class="checkbox-field">
            <input v-model="scheduleForm.is_default" type="checkbox" />
            <span>Mark as default schedule</span>
          </label>
        </div>
      </form>

      <template #actions>
        <button class="button-primary" type="button" :disabled="isSavingSchedule" @click="saveSchedule">
          {{ isSavingSchedule ? "Saving..." : editingScheduleId === null ? "Create schedule" : "Save schedule" }}
        </button>
      </template>
    </DialogModal>

    <DialogModal
      :open="isDayModalOpen"
      :title="editingScheduleDayId === null ? 'Create weekday rule' : 'Edit weekday rule'"
      description="Define the working-hours rule for one weekday in the selected schedule."
      @close="isDayModalOpen = false"
    >
      <form class="page-stack" @submit.prevent="saveScheduleDay">
        <div class="form-grid">
          <label class="field-group">
            <span class="field-label">Weekday</span>
            <select v-model="dayForm.weekday" class="select-input">
              <option v-for="label in weekdayLabels.map((value, index) => ({ value, index }))" :key="label.index" :value="label.index">
                {{ label.value }}
              </option>
            </select>
          </label>

          <label class="checkbox-field">
            <input v-model="dayForm.is_working_day" type="checkbox" />
            <span>Working day</span>
          </label>

          <label class="field-group">
            <span class="field-label">Capacity hours</span>
            <input v-model.number="dayForm.capacity_hours" class="text-input" type="number" min="0" step="1" :disabled="!dayForm.is_working_day" />
          </label>

          <label class="field-group">
            <span class="field-label">Start time</span>
            <input v-model="dayForm.start_time" class="text-input" type="time" :disabled="!dayForm.is_working_day" />
          </label>

          <label class="field-group">
            <span class="field-label">End time</span>
            <input v-model="dayForm.end_time" class="text-input" type="time" :disabled="!dayForm.is_working_day" />
          </label>
        </div>
      </form>

      <template #actions>
        <button class="button-primary" type="button" :disabled="isSavingDay" @click="saveScheduleDay">
          {{ isSavingDay ? "Saving..." : editingScheduleDayId === null ? "Create rule" : "Save rule" }}
        </button>
      </template>
    </DialogModal>
  </div>
</template>

<style scoped>
.checkbox-field {
  align-items: center;
  display: flex;
  gap: 0.65rem;
  min-height: 2.8rem;
}

.resource-item.is-selected {
  border-color: rgba(16, 125, 103, 0.4);
  box-shadow: 0 0 0 1px rgba(16, 125, 103, 0.12);
}
</style>
