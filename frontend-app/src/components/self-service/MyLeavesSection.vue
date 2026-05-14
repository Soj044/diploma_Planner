<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";

import { useAuth } from "../../composables/useAuth";
import { coreService } from "../../services/core-service";
import { describeRequestError } from "../../services/http";
import type { EmployeeLeave, EmployeeLeaveInput } from "../../types/api";

interface LeaveFormState {
  leave_type: string;
  status: string;
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

const statusOptions = [
  { value: "requested", label: "Requested" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "cancelled", label: "Cancelled" },
] as const;

const auth = useAuth();
const leaves = ref<EmployeeLeave[]>([]);
const isLoading = ref(false);
const isSaving = ref(false);
const deletingId = ref<number | null>(null);
const editingId = ref<number | null>(null);
const errorMessage = ref("");
const successMessage = ref("");

const form = reactive<LeaveFormState>({
  leave_type: "vacation",
  status: "requested",
  start_date: "",
  end_date: "",
  comment: "",
});

function resetForm() {
  form.leave_type = "vacation";
  form.status = "requested";
  form.start_date = "";
  form.end_date = "";
  form.comment = "";
  editingId.value = null;
}

function startEditing(leave: EmployeeLeave) {
  editingId.value = leave.id;
  form.leave_type = leave.leave_type;
  form.status = leave.status;
  form.start_date = leave.start_date;
  form.end_date = leave.end_date;
  form.comment = leave.comment;
  errorMessage.value = "";
  successMessage.value = "";
}

async function load() {
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

function buildPayload(): EmployeeLeaveInput | null {
  if (auth.employeeId.value === null) {
    errorMessage.value = "Employee profile is required for self-service leaves.";
    return null;
  }

  return {
    employee: auth.employeeId.value,
    leave_type: form.leave_type,
    status: form.status,
    start_date: form.start_date,
    end_date: form.end_date,
    comment: form.comment.trim(),
  };
}

async function save() {
  const payload = buildPayload();
  if (!payload) {
    return;
  }

  isSaving.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    await (editingId.value === null
      ? coreService.createEmployeeLeave(payload)
      : coreService.updateEmployeeLeave(editingId.value, payload));

    successMessage.value = editingId.value === null ? "Employee leave created." : "Employee leave updated.";
    resetForm();
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isSaving.value = false;
  }
}

async function remove(id: number) {
  deletingId.value = id;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    await coreService.deleteEmployeeLeave(id);
    successMessage.value = "Employee leave deleted.";
    if (editingId.value === id) {
      resetForm();
    }
    await load();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    deletingId.value = null;
  }
}

onMounted(async () => {
  await load();
  resetForm();
});
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <p class="eyebrow">Employee self-service</p>
      <h3 class="page-title">Own leave requests and periods</h3>
      <p class="page-description">
        Track your own leave requests and update them while they are still pending.
      </p>
    </section>

    <div v-if="auth.employeeId.value === null" class="notice">
      Employee profile is missing, so self-service leave management cannot be used from this account.
    </div>

    <section v-else class="page-card">
      <div class="data-layout">
        <form class="editor-card" @submit.prevent="save">
          <div class="editor-header">
            <div>
              <p class="section-caption">{{ editingId === null ? "Create leave" : "Edit leave" }}</p>
              <p class="resource-copy">Choose dates, leave type, and an optional comment for your request.</p>
            </div>
            <div class="inline-actions">
              <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
              <button
                v-if="editingId !== null"
                class="button-secondary"
                type="button"
                :disabled="isSaving"
                @click="resetForm"
              >
                Cancel edit
              </button>
            </div>
          </div>

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
              <span class="field-label">Status</span>
              <select v-model="form.status" class="select-input">
                <option v-for="option in statusOptions" :key="option.value" :value="option.value">
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

          <div class="action-row">
            <button class="button-primary" type="submit" :disabled="isSaving">
              {{ isSaving ? "Saving..." : editingId === null ? "Create leave" : "Save leave" }}
            </button>
          </div>
        </form>

        <div class="records-card">
          <div class="editor-header">
            <div>
              <p class="section-caption">Existing leaves</p>
              <p class="resource-copy">Employee scope is enforced by backend and mirrored here only for UX clarity.</p>
            </div>
            <span class="pill">{{ leaves.length }} rows</span>
          </div>

          <p v-if="isLoading" class="resource-copy">Loading...</p>
          <p v-else-if="leaves.length === 0" class="empty-state">No leave records yet.</p>
          <ul v-else class="resource-list">
            <li v-for="leave in leaves" :key="leave.id" class="resource-item">
              <div class="resource-heading">
                <p class="resource-label">{{ leave.leave_type }}</p>
                <div class="inline-actions">
                  <button class="button-secondary" type="button" @click="startEditing(leave)">Edit</button>
                  <button
                    class="button-danger"
                    type="button"
                    :disabled="deletingId === leave.id"
                    @click="remove(leave.id)"
                  >
                    {{ deletingId === leave.id ? "Deleting..." : "Delete" }}
                  </button>
                </div>
              </div>
              <div class="pill-row">
                <span class="pill">{{ leave.status }}</span>
              </div>
              <p class="resource-copy">{{ leave.start_date }} - {{ leave.end_date }}</p>
              <p class="resource-copy">{{ leave.comment || "No comment." }}</p>
              <p class="item-meta">Leave ID {{ leave.id }} · updated {{ new Date(leave.updated_at).toLocaleString() }}</p>
            </li>
          </ul>
        </div>
      </div>

      <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
      <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>
    </section>
  </div>
</template>
