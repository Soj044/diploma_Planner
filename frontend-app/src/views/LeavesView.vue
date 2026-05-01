<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import DialogModal from "../components/DialogModal.vue";
import SectionPlaceholder from "../components/SectionPlaceholder.vue";
import { useAuth } from "../composables/useAuth";
import { coreService } from "../services/core-service";
import { describeRequestError } from "../services/http";
import type { EmployeeLeave, EmployeeLeaveInput } from "../types/api";

interface LeaveFormState {
  leave_type: string;
  start_date: string;
  end_date: string;
  comment: string;
}

const leaveTypeOptions = [
  { value: "vacation", label: "Vacation" },
  { value: "sick_leave", label: "Sick leave" },
  { value: "day_off", label: "Day off" },
  { value: "business_trip", label: "Business trip" },
] as const;

const auth = useAuth();
const leaves = ref<EmployeeLeave[]>([]);
const isLoading = ref(false);
const isSaving = ref(false);
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

const sortedLeaves = computed(() => {
  return [...leaves.value].sort((left, right) => right.start_date.localeCompare(left.start_date));
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
  if (auth.role.value !== "employee") {
    return;
  }

  isLoading.value = true;
  errorMessage.value = "";

  try {
    leaves.value = await coreService.listEmployeeLeaves();
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

onMounted(load);
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Leaves</p>
      <h3 class="page-title">
        {{ auth.role.value === "employee" ? "Your leave requests" : "Leave queue" }}
      </h3>
      <p class="page-description">
        {{
          auth.role.value === "employee"
            ? "Employees can create leave requests and modify them only while they remain requested."
            : "Manager/admin leave review stays deferred in this slice. The route remains reserved for the requested queue."
        }}
      </p>
      <div class="pill-row">
        <span class="pill">/leaves</span>
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

    <SectionPlaceholder
      v-else
      eyebrow="Canonical route"
      title="Manager/admin queue follows in the next stage"
      description="This route remains the future home of the requested-leaves queue backed by POST /employee-leaves/{id}/set-status/."
    >
      <div class="notice">
        Keep manager/admin leave decisions on the backend status action. This slice only ships employee self-service.
      </div>
    </SectionPlaceholder>

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
