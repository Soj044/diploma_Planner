<script setup lang="ts">
import { reactive, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { useAuth } from "../composables/useAuth";
import { describeRequestError } from "../services/http";

const auth = useAuth();
const router = useRouter();

const form = reactive({
  email: "",
  password: "",
  username: "",
  first_name: "",
  last_name: "",
});

const isSubmitting = ref(false);
const errorMessage = ref("");

async function handleSubmit() {
  isSubmitting.value = true;
  errorMessage.value = "";

  try {
    await auth.signup({
      email: form.email.trim(),
      password: form.password,
      username: form.username.trim() || undefined,
      first_name: form.first_name.trim() || undefined,
      last_name: form.last_name.trim() || undefined,
    });
    await router.replace("/");
  } catch (error: unknown) {
    errorMessage.value = describeRequestError(error);
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <div class="auth-layout">
    <section class="auth-card">
      <p class="eyebrow">Employee onboarding</p>
      <h1 class="page-title">Создать employee account</h1>
      <p class="page-description">
        Backend signup создаёт только `employee` роль и автоматически поднимает employee profile. Manager/admin
        аккаунты должны входить через уже созданные учётные записи.
      </p>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <div class="form-grid">
          <label class="field-group">
            <span class="field-label">Email</span>
            <input v-model.trim="form.email" class="text-input" type="email" autocomplete="email" required />
          </label>

          <label class="field-group">
            <span class="field-label">Username</span>
            <input v-model.trim="form.username" class="text-input" autocomplete="username" />
          </label>

          <label class="field-group">
            <span class="field-label">First name</span>
            <input v-model.trim="form.first_name" class="text-input" autocomplete="given-name" />
          </label>

          <label class="field-group">
            <span class="field-label">Last name</span>
            <input v-model.trim="form.last_name" class="text-input" autocomplete="family-name" />
          </label>

          <label class="field-group field-group-span-2">
            <span class="field-label">Password</span>
            <input
              v-model="form.password"
              class="text-input"
              type="password"
              autocomplete="new-password"
              minlength="8"
              required
            />
          </label>
        </div>

        <div class="action-row">
          <button class="button-primary" type="submit" :disabled="isSubmitting">
            {{ isSubmitting ? "Creating..." : "Create employee account" }}
          </button>
        </div>

        <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
      </form>

      <p class="auth-copy">
        Уже есть аккаунт?
        <RouterLink class="auth-link" to="/login">Перейти ко входу</RouterLink>
      </p>
    </section>
  </div>
</template>
