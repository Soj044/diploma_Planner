<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";

import SectionPlaceholder from "../SectionPlaceholder.vue";
import { coreService } from "../../services/core-service";
import { describeRequestError } from "../../services/http";
import type { User, UserInput } from "../../types/api";

const roleOptions = [
  { label: "Admin", value: "admin" },
  { label: "Manager", value: "manager" },
  { label: "Employee", value: "employee" },
] as const;

const users = ref<User[]>([]);
const isLoading = ref(false);
const isSaving = ref(false);
const deletingId = ref<number | null>(null);
const editingId = ref<number | null>(null);
const errorMessage = ref("");
const successMessage = ref("");

const form = reactive<UserInput>({
  email: "",
  username: "",
  password: "",
  first_name: "",
  last_name: "",
  role: "manager",
  is_active: true,
});

function resetForm() {
  form.email = "";
  form.username = "";
  form.password = "";
  form.first_name = "";
  form.last_name = "";
  form.role = "manager";
  form.is_active = true;
  editingId.value = null;
}

function startEditing(user: User) {
  editingId.value = user.id;
  form.email = user.email;
  form.username = user.username;
  form.password = "";
  form.first_name = user.first_name;
  form.last_name = user.last_name;
  form.role = user.role;
  form.is_active = user.is_active;
  errorMessage.value = "";
  successMessage.value = "";
}

async function load() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    users.value = await coreService.listUsers();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

function buildPayload(): UserInput {
  const payload: UserInput = {
    email: form.email.trim(),
    username: form.username.trim(),
    first_name: form.first_name.trim(),
    last_name: form.last_name.trim(),
    role: form.role,
    is_active: form.is_active,
  };

  if (form.password?.trim()) {
    payload.password = form.password.trim();
  }

  return payload;
}

async function save() {
  isSaving.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const payload = buildPayload();
    if (editingId.value === null) {
      await coreService.createUser(payload);
      successMessage.value = "User created.";
    } else {
      await coreService.updateUser(editingId.value, payload);
      successMessage.value = "User updated.";
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
    await coreService.deleteUser(id);
    successMessage.value = "User deleted.";
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
    eyebrow="Users"
    title="User accounts for managers and employees"
    description="Minimal CRUD over /users/ for the accounts that back employee profiles and manager ownership."
  >
    <div class="data-layout">
      <form class="editor-card" @submit.prevent="save">
        <div class="editor-header">
          <div>
            <p class="section-caption">{{ editingId === null ? "Create user" : "Edit user" }}</p>
            <p class="resource-path">/users/</p>
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
            <span class="field-label">Email</span>
            <input v-model.trim="form.email" class="text-input" type="email" required />
          </label>

          <label class="field-group">
            <span class="field-label">Username</span>
            <input v-model.trim="form.username" class="text-input" required />
          </label>

          <label class="field-group">
            <span class="field-label">{{ editingId === null ? "Password" : "Password (optional)" }}</span>
            <input
              v-model="form.password"
              class="text-input"
              type="password"
              :required="editingId === null"
              autocomplete="new-password"
            />
          </label>

          <label class="field-group">
            <span class="field-label">Role</span>
            <select v-model="form.role" class="select-input">
              <option v-for="role in roleOptions" :key="role.value" :value="role.value">{{ role.label }}</option>
            </select>
          </label>

          <label class="field-group">
            <span class="field-label">First name</span>
            <input v-model.trim="form.first_name" class="text-input" />
          </label>

          <label class="field-group">
            <span class="field-label">Last name</span>
            <input v-model.trim="form.last_name" class="text-input" />
          </label>

          <label class="field-group field-group-span-2 checkbox-row">
            <input v-model="form.is_active" class="check-input" type="checkbox" />
            <span class="field-label">Active account</span>
          </label>
        </div>

        <div class="action-row">
          <button class="button-primary" type="submit" :disabled="isSaving">
            {{ isSaving ? "Saving..." : editingId === null ? "Create user" : "Save user" }}
          </button>
        </div>

        <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
        <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>
      </form>

      <div class="records-card">
        <div class="editor-header">
          <div>
            <p class="section-caption">Existing users</p>
            <p class="resource-copy">Useful before employee creation because employee profiles reference /users/.</p>
          </div>
          <span class="pill">{{ users.length }} rows</span>
        </div>

        <p v-if="isLoading" class="resource-copy">Loading...</p>
        <p v-else-if="users.length === 0" class="empty-state">No users yet.</p>
        <ul v-else class="resource-list">
          <li v-for="user in users" :key="user.id" class="resource-item">
            <div class="resource-heading">
              <p class="resource-label">{{ user.email }}</p>
              <div class="inline-actions">
                <button class="button-secondary" type="button" @click="startEditing(user)">Edit</button>
                <button
                  class="button-danger"
                  type="button"
                  :disabled="deletingId === user.id"
                  @click="remove(user.id)"
                >
                  {{ deletingId === user.id ? "Deleting..." : "Delete" }}
                </button>
              </div>
            </div>
            <div class="pill-row">
              <span class="pill">{{ user.role }}</span>
              <span class="pill" :class="{ 'is-danger': !user.is_active }">
                {{ user.is_active ? "active" : "inactive" }}
              </span>
            </div>
            <p class="resource-copy">
              Username: {{ user.username }}<span v-if="user.first_name || user.last_name">
                · {{ [user.first_name, user.last_name].filter(Boolean).join(" ") }}
              </span>
            </p>
            <p class="item-meta">ID {{ user.id }} · updated {{ new Date(user.updated_at).toLocaleString() }}</p>
          </li>
        </ul>
      </div>
    </div>
  </SectionPlaceholder>
</template>
