<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import SectionPlaceholder from "../SectionPlaceholder.vue";
import { coreService } from "../../services/core-service";
import { describeRequestError } from "../../services/http";
import type { Department, Employee, EmployeeInput, User } from "../../types/api";

interface EmployeeFormState {
  user: string;
  department: string;
  full_name: string;
  position_name: string;
  employment_type: string;
  weekly_capacity_hours: number;
  timezone: string;
  hire_date: string;
  is_active: boolean;
}

const employmentOptions = [
  { label: "Full time", value: "full_time" },
  { label: "Part time", value: "part_time" },
  { label: "Contract", value: "contract" },
] as const;

const employees = ref<Employee[]>([]);
const users = ref<User[]>([]);
const departments = ref<Department[]>([]);
const isLoading = ref(false);
const isSaving = ref(false);
const deletingId = ref<number | null>(null);
const editingId = ref<number | null>(null);
const errorMessage = ref("");
const successMessage = ref("");

const form = reactive<EmployeeFormState>({
  user: "",
  department: "",
  full_name: "",
  position_name: "",
  employment_type: "full_time",
  weekly_capacity_hours: 40,
  timezone: "UTC",
  hire_date: "",
  is_active: true,
});

const userNameById = computed(() => {
  return new Map(users.value.map((user) => [user.id, user.email]));
});

const departmentNameById = computed(() => {
  return new Map(departments.value.map((department) => [department.id, department.name]));
});

const availableUsers = computed(() => {
  const reservedUserIds = new Set(
    employees.value
      .filter((employee) => employee.id !== editingId.value)
      .map((employee) => employee.user),
  );

  return users.value.filter((user) => !reservedUserIds.has(user.id));
});

function resetForm() {
  form.user = "";
  form.department = "";
  form.full_name = "";
  form.position_name = "";
  form.employment_type = "full_time";
  form.weekly_capacity_hours = 40;
  form.timezone = "UTC";
  form.hire_date = "";
  form.is_active = true;
  editingId.value = null;
}

function startEditing(employee: Employee) {
  editingId.value = employee.id;
  form.user = String(employee.user);
  form.department = employee.department === null ? "" : String(employee.department);
  form.full_name = employee.full_name;
  form.position_name = employee.position_name;
  form.employment_type = employee.employment_type;
  form.weekly_capacity_hours = employee.weekly_capacity_hours;
  form.timezone = employee.timezone;
  form.hire_date = employee.hire_date || "";
  form.is_active = employee.is_active;
  errorMessage.value = "";
  successMessage.value = "";
}

async function load() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    const [employeeRows, userRows, departmentRows] = await Promise.all([
      coreService.listEmployees(),
      coreService.listUsers(),
      coreService.listDepartments(),
    ]);
    employees.value = employeeRows;
    users.value = userRows;
    departments.value = departmentRows;
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

function buildPayload(): EmployeeInput {
  return {
    user: Number(form.user),
    department: form.department ? Number(form.department) : null,
    full_name: form.full_name.trim(),
    position_name: form.position_name.trim(),
    employment_type: form.employment_type,
    weekly_capacity_hours: Number(form.weekly_capacity_hours),
    timezone: form.timezone.trim() || "UTC",
    hire_date: form.hire_date || null,
    is_active: form.is_active,
  };
}

async function save() {
  isSaving.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const payload = buildPayload();
    if (editingId.value === null) {
      await coreService.createEmployee(payload);
      successMessage.value = "Employee created.";
    } else {
      await coreService.updateEmployee(editingId.value, payload);
      successMessage.value = "Employee updated.";
    }

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
    await coreService.deleteEmployee(id);
    successMessage.value = "Employee deleted.";
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

onMounted(load);
</script>

<template>
  <SectionPlaceholder
    eyebrow="Employees"
    title="Employee profiles linked to users and departments"
    description="This is the last reference-data slice needed before tasks start to become meaningful and before later planner-specific entities are added."
  >
    <div class="data-layout">
      <form class="editor-card" @submit.prevent="save">
        <div class="editor-header">
          <div>
            <p class="section-caption">{{ editingId === null ? "Create employee" : "Edit employee" }}</p>
            <p class="resource-path">/employees/</p>
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

        <div v-if="availableUsers.length === 0 && editingId === null" class="notice">
          Create another core user before adding a new employee profile. `Employee.user` is required and one-to-one.
        </div>

        <div class="form-grid">
          <label class="field-group">
            <span class="field-label">User</span>
            <select v-model="form.user" class="select-input" required>
              <option value="">Select user</option>
              <option v-for="user in availableUsers" :key="user.id" :value="String(user.id)">{{ user.email }}</option>
              <option
                v-if="
                  editingId !== null &&
                  form.user &&
                  !availableUsers.some((user) => String(user.id) === form.user) &&
                  userNameById.get(Number(form.user))
                "
                :value="form.user"
              >
                {{ userNameById.get(Number(form.user)) }}
              </option>
            </select>
          </label>

          <label class="field-group">
            <span class="field-label">Department</span>
            <select v-model="form.department" class="select-input">
              <option value="">No department</option>
              <option
                v-for="department in departments"
                :key="department.id"
                :value="String(department.id)"
              >
                {{ department.name }}
              </option>
            </select>
          </label>

          <label class="field-group">
            <span class="field-label">Full name</span>
            <input v-model.trim="form.full_name" class="text-input" required />
          </label>

          <label class="field-group">
            <span class="field-label">Position name</span>
            <input v-model.trim="form.position_name" class="text-input" required />
          </label>

          <label class="field-group">
            <span class="field-label">Employment type</span>
            <select v-model="form.employment_type" class="select-input">
              <option v-for="option in employmentOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <label class="field-group">
            <span class="field-label">Weekly capacity hours</span>
            <input v-model.number="form.weekly_capacity_hours" class="text-input" min="1" type="number" required />
          </label>

          <label class="field-group">
            <span class="field-label">Timezone</span>
            <input v-model.trim="form.timezone" class="text-input" />
          </label>

          <label class="field-group">
            <span class="field-label">Hire date</span>
            <input v-model="form.hire_date" class="text-input" type="date" />
          </label>

          <label class="field-group field-group-span-2 checkbox-row">
            <input v-model="form.is_active" class="check-input" type="checkbox" />
            <span class="field-label">Employee is active</span>
          </label>
        </div>

        <div class="action-row">
          <button class="button-primary" type="submit" :disabled="isSaving || (!form.user && editingId === null)">
            {{ isSaving ? "Saving..." : editingId === null ? "Create employee" : "Save employee" }}
          </button>
        </div>

        <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
        <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>
      </form>

      <div class="records-card">
        <div class="editor-header">
          <div>
            <p class="section-caption">Existing employees</p>
            <p class="resource-copy">These profiles will later feed employee skills, schedules, leaves, and planning runs.</p>
          </div>
          <span class="pill">{{ employees.length }} rows</span>
        </div>

        <p v-if="isLoading" class="resource-copy">Loading...</p>
        <p v-else-if="employees.length === 0" class="empty-state">No employees yet.</p>
        <ul v-else class="resource-list">
          <li v-for="employee in employees" :key="employee.id" class="resource-item">
            <div class="resource-heading">
              <p class="resource-label">{{ employee.full_name }}</p>
              <div class="inline-actions">
                <button class="button-secondary" type="button" @click="startEditing(employee)">Edit</button>
                <button
                  class="button-danger"
                  type="button"
                  :disabled="deletingId === employee.id"
                  @click="remove(employee.id)"
                >
                  {{ deletingId === employee.id ? "Deleting..." : "Delete" }}
                </button>
              </div>
            </div>
            <div class="pill-row">
              <span class="pill">{{ employee.employment_type }}</span>
              <span class="pill" :class="{ 'is-danger': !employee.is_active }">
                {{ employee.is_active ? "active" : "inactive" }}
              </span>
            </div>
            <p class="resource-copy">
              User: {{ userNameById.get(employee.user) || `#${employee.user}` }}
              · Department: {{ employee.department === null ? "None" : departmentNameById.get(employee.department) || `#${employee.department}` }}
            </p>
            <p class="resource-copy">
              Position: {{ employee.position_name }} · Capacity: {{ employee.weekly_capacity_hours }}h/week · Timezone:
              {{ employee.timezone }}
            </p>
            <p class="item-meta">ID {{ employee.id }} · updated {{ new Date(employee.updated_at).toLocaleString() }}</p>
          </li>
        </ul>
      </div>
    </div>
  </SectionPlaceholder>
</template>
