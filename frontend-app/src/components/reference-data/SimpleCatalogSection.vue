<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import SectionPlaceholder from "../SectionPlaceholder.vue";
import { describeRequestError } from "../../services/http";
import type { DepartmentInput, SkillInput } from "../../types/api";

interface CatalogItem {
  id: number;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

type CatalogInput = DepartmentInput | SkillInput;

const props = withDefaults(defineProps<{
  eyebrow: string;
  title: string;
  description: string;
  endpoint: string;
  entityLabel: string;
  loadItems: () => Promise<CatalogItem[]>;
  createItem: (payload: CatalogInput) => Promise<CatalogItem>;
  updateItem: (id: number, payload: CatalogInput) => Promise<CatalogItem>;
  deleteItem: (id: number) => Promise<void>;
  allowCreate?: boolean;
  allowEdit?: boolean;
  allowDelete?: boolean;
}>(), {
  allowCreate: true,
  allowEdit: true,
  allowDelete: true,
});

const items = ref<CatalogItem[]>([]);
const isLoading = ref(false);
const isSaving = ref(false);
const deletingId = ref<number | null>(null);
const editingId = ref<number | null>(null);
const errorMessage = ref("");
const successMessage = ref("");

const form = reactive<CatalogInput>({
  name: "",
  description: "",
});

const hasEditor = computed(() => props.allowCreate || props.allowEdit);

function resetForm() {
  form.name = "";
  form.description = "";
  editingId.value = null;
}

function startEditing(item: CatalogItem) {
  if (!props.allowEdit) {
    return;
  }

  editingId.value = item.id;
  form.name = item.name;
  form.description = item.description;
  successMessage.value = "";
  errorMessage.value = "";
}

async function load() {
  isLoading.value = true;
  errorMessage.value = "";

  try {
    items.value = await props.loadItems();
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

async function save() {
  if ((editingId.value === null && !props.allowCreate) || (editingId.value !== null && !props.allowEdit)) {
    return;
  }

  isSaving.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const payload: CatalogInput = {
      name: form.name.trim(),
      description: form.description.trim(),
    };

    if (editingId.value === null) {
      await props.createItem(payload);
      successMessage.value = `${props.entityLabel} created.`;
    } else {
      await props.updateItem(editingId.value, payload);
      successMessage.value = `${props.entityLabel} updated.`;
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
  if (!props.allowDelete) {
    return;
  }

  deletingId.value = id;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    await props.deleteItem(id);
    successMessage.value = `${props.entityLabel} deleted.`;
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
  <SectionPlaceholder :eyebrow="eyebrow" :title="title" :description="description">
    <div class="data-layout" :class="{ 'data-layout-single': !hasEditor }">
      <form v-if="hasEditor" class="editor-card" @submit.prevent="save">
        <div class="editor-header">
          <div>
            <p class="section-caption">{{ editingId === null ? `Create ${entityLabel}` : `Edit ${entityLabel}` }}</p>
            <p class="resource-path">{{ endpoint }}</p>
          </div>
          <div class="inline-actions">
            <button class="button-secondary" type="button" :disabled="isLoading" @click="load">Refresh</button>
            <button
              v-if="editingId !== null && allowEdit"
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
            <span class="field-label">Name</span>
            <input v-model.trim="form.name" class="text-input" required />
          </label>

          <label class="field-group field-group-span-2">
            <span class="field-label">Description</span>
            <textarea v-model.trim="form.description" class="text-area" rows="4" />
          </label>
        </div>

        <div class="action-row">
          <button class="button-primary" type="submit" :disabled="isSaving">
            {{ isSaving ? "Saving..." : editingId === null ? `Create ${entityLabel}` : `Save ${entityLabel}` }}
          </button>
        </div>

        <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
        <p v-if="successMessage" class="status-banner is-success">{{ successMessage }}</p>
      </form>

      <div class="records-card">
        <div class="editor-header">
          <div>
            <p class="section-caption">Existing {{ title }}</p>
            <p class="resource-copy">Direct DRF list view rendered without client-owned shadow state.</p>
          </div>
          <span class="pill">{{ items.length }} rows</span>
        </div>

        <div v-if="!hasEditor" class="notice">
          This role has read-only access to {{ title.toLowerCase() }}.
        </div>

        <p v-if="isLoading" class="resource-copy">Loading...</p>
        <p v-else-if="items.length === 0" class="empty-state">No records yet.</p>
        <ul v-else class="resource-list">
          <li v-for="item in items" :key="item.id" class="resource-item">
            <div class="resource-heading">
              <p class="resource-label">{{ item.name }}</p>
              <div v-if="allowEdit || allowDelete" class="inline-actions">
                <button class="button-secondary" type="button" @click="startEditing(item)">Edit</button>
                <button
                  v-if="allowDelete"
                  class="button-danger"
                  type="button"
                  :disabled="deletingId === item.id"
                  @click="remove(item.id)"
                >
                  {{ deletingId === item.id ? "Deleting..." : "Delete" }}
                </button>
              </div>
            </div>
            <p class="resource-copy">{{ item.description || "No description." }}</p>
            <p class="item-meta">ID {{ item.id }} · updated {{ new Date(item.updated_at).toLocaleString() }}</p>
          </li>
        </ul>
      </div>
    </div>
  </SectionPlaceholder>
</template>
