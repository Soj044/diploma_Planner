<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import DialogModal from "../components/DialogModal.vue";
import { useAuth } from "../composables/useAuth";
import { coreService } from "../services/core-service";
import { describeRequestError } from "../services/http";
import type { Employee, EmployeeLeave, EmployeeLeaveInput } from "../types/api";

interface LeaveFormState {
  leave_type: string;
  start_date: string;
  end_date: string;
  comment: string;
}

interface LeaveQueueRow {
  leave: EmployeeLeave;
  employee: Employee | null;
}

const leaveTypeOptions = [
  { value: "vacation", label: "Vacation" },
  { value: "sick_leave", label: "Sick leave" },
  { value: "day_off", label: "Day off" },
  { value: "business_trip", label: "Business trip" },
] as const;

const auth = useAuth();
const employees = ref<Employee[]>([]);
const leaves = ref<EmployeeLeave[]>([]);
const isLoading = ref(false);
const isSaving = ref(false);
const actingLeaveId = ref<number | null>(null);
const deletingId = ref<number | null>(null);
const editingLeaveId = ref<number | null>(null);
const errorMessage = ref("");
const successMessage = ref("");
const isModalOpen = ref(false);

const form = reactive<LeaveFormState>({
  leave_type: "vacation",
  start_date: "",
  end_date: "",
  comment: "",
});

const employeeById = computed(() => {
  return new Map(employees.value.map((employee) => [employee.id, employee]));
});

const sortedLeaves = computed(() => {
  return [...leaves.value].sort((left, right) => right.start_date.localeCompare(left.start_date));
});

const queueRows = computed<LeaveQueueRow[]>(() => {
  return leaves.value
    .filter((leave) => leave.status === "requested")
    .sort((left, right) => left.start_date.localeCompare(right.start_date))
    .map((leave) => ({
      leave,
      employee: employeeById.value.get(leave.employee) ?? null,
    }));
});

const modalTitle = computed(() => (editingLeaveId.value === null ? "Create leave" : "Edit requested leave"));

function canEditLeave(leave: EmployeeLeave) {
  return leave.status === "requested";
}

function resetForm() {
  editingLeaveId.value = null;
  form.leave_type = "vacation";
  form.start_date = "";
  form.end_date = "";
  form.comment = "";
}

function openCreateModal() {
  resetForm();
  errorMessage.value = "";
  successMessage.value = "";
  isModalOpen.value = true;
}

function openEditModal(leave: EmployeeLeave) {
  editingLeaveId.value = leave.id;
  form.leave_type = leave.leave_type;
  form.start_date = leave.start_date;
  form.end_date = leave.end_date;
  form.comment = leave.comment;
  errorMessage.value = "";
  successMessage.value = "";
  isModalOpen.value = true;
}

function buildPayload(): EmployeeLeaveInput | null {
  if (auth.employeeId.value === null) {
    errorMessage.value = "Employee profile is required for self-service leaves.";
    return null;
  }

  return {
    employee: auth.employeeId.value,
    leave_type: form.leave_type,
    start_date: form.start_date,
    end_date: form.end_date,
    comment: form.comment.trim(),
  };
}

async function load() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    if (auth.role.value === "employee") {
      leaves.value = await coreService.listEmployeeLeaves();
      employees.value = [];
      return;
    }

    const [leaveRows, employeeRows] = await Promise.all([
      coreService.listEmployeeLeaves(),
      coreService.listEmployees(),
    ]);
    leaves.value = leaveRows;
    employees.value = employeeRows;
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

async function saveLeave() {
  const payload = buildPayload();
  if (!payload) {
    return;
  }

  isSaving.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    await (editingLeaveId.value === null
      ? coreService.createEmployeeLeave(payload)
      : coreService.updateEmployeeLeave(editingLeaveId.value, payload));

    successMessage.value = editingLeaveId.value === null ? "Leave created." : "Requested leave updated.";
    isModalOpen.value = false;
    resetForm();
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isSaving.value = false;
  }
}

async function removeLeave(id: number) {
  deletingId.value = id;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    await coreService.deleteEmployeeLeave(id);
    successMessage.value = "Requested leave deleted.";
    if (editingLeaveId.value === id) {
      isModalOpen.value = false;
      resetForm();
    }
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    deletingId.value = null;
  }
}

async function setLeaveStatus(leave: EmployeeLeave, status: "approved" | "rejected") {
  actingLeaveId.value = leave.id;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    await coreService.setEmployeeLeaveStatus(leave.id, { status });
    successMessage.value = status === "approved" ? "Leave approved." : "Leave rejected.";
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    actingLeaveId.value = null;
  }
}

onMounted(load);
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Leaves</p>
      <h3 class="page-title">
        {{ auth.role.value === "employee" ? "Your leave requests" : "Requested leave queue" }}
      </h3>
      <p class="page-description">
        {{
          auth.role.value === "employee"
            ? "Employees can create leave requests and modify them only while they remain requested."
            : "Managers and admins review only requested leave records and decide them through the backend status action."
        }}
      </p>
      <div class="pill-row">
        <span class="pill is-warm">{{ auth.role.value ?? "unknown role" }}</span>
      </div>
    </section>

    <section v-if="auth.role.value === 'employee'" class="page-card">
      <div class="editor-header">
        <div>
          <p class="section-caption">Leave history</p>
          <p class="resource-copy">Status is backend-owned. The employee UI no longer exposes direct status editing.</p>
        </div>
        <div class="inline-actions">
          <button class="button-primary" type="button" @click="openCreateModal">Create leave</button>
          <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
        </div>
      </div>

      <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
      <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>
      <p v-if="isLoading" class="resource-copy">Loading leave requests...</p>
      <p v-else-if="sortedLeaves.length === 0" class="empty-state">No leave records yet.</p>
      <ul v-else class="resource-list">
        <li v-for="leave in sortedLeaves" :key="leave.id" class="resource-item">
          <div class="resource-heading">
            <p class="resource-label">{{ leave.leave_type }}</p>
            <div class="inline-actions">
              <button
                v-if="canEditLeave(leave)"
                class="button-secondary"
                type="button"
                @click="openEditModal(leave)"
              >
                Edit
              </button>
              <button
                v-if="canEditLeave(leave)"
                class="button-danger"
                type="button"
                :disabled="deletingId === leave.id"
                @click="removeLeave(leave.id)"
              >
                {{ deletingId === leave.id ? "Deleting..." : "Delete" }}
              </button>
            </div>
          </div>
          <div class="pill-row">
            <span class="pill" :class="{ 'is-warm': leave.status !== 'requested' }">{{ leave.status }}</span>
          </div>
          <p class="resource-copy">{{ leave.start_date }} → {{ leave.end_date }}</p>
          <p class="resource-copy">{{ leave.comment || "No comment." }}</p>
          <p class="item-meta">Leave #{{ leave.id }} · updated {{ new Date(leave.updated_at).toLocaleString() }}</p>
        </li>
      </ul>
    </section>

    <section v-else class="page-card">
      <div class="editor-header">
        <div>
          <p class="section-caption">Requested queue</p>
          <p class="resource-copy">
            Review pending leave requests here and decide them without leaving the queue.
          </p>
        </div>
        <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
      </div>

      <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
      <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>
      <p v-if="isLoading" class="resource-copy">Loading requested leave queue...</p>
      <p v-else-if="queueRows.length === 0" class="empty-state">No requested leave records are waiting for review.</p>
      <ul v-else class="resource-list">
        <li v-for="row in queueRows" :key="row.leave.id" class="resource-item">
          <div class="resource-heading">
            <div>
              <p class="resource-label">
                {{ row.employee?.full_name || `Employee #${row.leave.employee}` }}
              </p>
              <p class="resource-copy">
                {{ row.employee?.position_name || "Position not set" }} · {{ row.leave.leave_type }}
              </p>
            </div>
            <div class="inline-actions">
              <button
                class="button-primary"
                type="button"
                :disabled="actingLeaveId === row.leave.id"
                @click="setLeaveStatus(row.leave, 'approved')"
              >
                {{ actingLeaveId === row.leave.id ? "Saving..." : "Approve" }}
              </button>
              <button
                class="button-danger"
                type="button"
                :disabled="actingLeaveId === row.leave.id"
                @click="setLeaveStatus(row.leave, 'rejected')"
              >
                {{ actingLeaveId === row.leave.id ? "Saving..." : "Reject" }}
              </button>
            </div>
          </div>

          <div class="pill-row">
            <span class="pill">requested</span>
          </div>
          <p class="resource-copy">{{ row.leave.start_date }} → {{ row.leave.end_date }}</p>
          <p class="resource-copy">{{ row.leave.comment || "No comment." }}</p>
          <p class="item-meta">
            Leave #{{ row.leave.id }} · updated {{ new Date(row.leave.updated_at).toLocaleString() }}
          </p>
        </li>
      </ul>
    </section>

    <DialogModal
      :open="isModalOpen"
      :title="modalTitle"
      description="Leave requests are always created in requested status. Requested leaves are the only ones that can be edited or deleted."
      @close="isModalOpen = false"
    >
      <form class="page-stack" @submit.prevent="saveLeave">
        <div class="form-grid">
          <label class="field-group">
            <span class="field-label">Leave type</span>
            <select v-model="form.leave_type" class="select-input">
              <option v-for="option in leaveTypeOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <label class="field-group">
            <span class="field-label">Start date</span>
            <input v-model="form.start_date" class="text-input" type="date" required />
          </label>

          <label class="field-group">
            <span class="field-label">End date</span>
            <input v-model="form.end_date" class="text-input" type="date" required />
          </label>

          <label class="field-group field-group-span-2">
            <span class="field-label">Comment</span>
            <textarea v-model.trim="form.comment" class="text-area" rows="4" />
          </label>
        </div>
      </form>

      <template #actions>
        <button class="button-primary" type="button" :disabled="isSaving" @click="saveLeave">
          {{ isSaving ? "Saving..." : editingLeaveId === null ? "Create leave" : "Save leave" }}
        </button>
      </template>
    </DialogModal>
  </div>
</template>
