<script setup lang="ts">
import { reactive, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { useAuth } from "../composables/useAuth";
import { describeRequestError } from "../services/http";

const auth = useAuth();
const route = useRoute();
const router = useRouter();

const form = reactive({
  email: "",
  password: "",
});

const isSubmitting = ref(false);
const errorMessage = ref("");

function resolveRedirect(): string {
  return typeof route.query.redirect === "string" && route.query.redirect.startsWith("/")
    ? route.query.redirect
    : "/";
}

async function handleSubmit() {
  isSubmitting.value = true;
  errorMessage.value = "";

  try {
    await auth.login({
      email: form.email.trim(),
      password: form.password,
    });
    await router.replace(resolveRedirect());
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
      <p class="eyebrow">Workestrator</p>
      <h1 class="page-title">Вход в manager shell</h1>
      <p class="page-description">
        Используй существующую учётную запись `core-service`. Access token хранится только в памяти браузера, refresh
        идёт через HttpOnly cookie.
      </p>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <label class="field-group">
          <span class="field-label">Email</span>
          <input v-model.trim="form.email" class="text-input" type="email" autocomplete="email" required />
        </label>

        <label class="field-group">
          <span class="field-label">Password</span>
          <input
            v-model="form.password"
            class="text-input"
            type="password"
            autocomplete="current-password"
            required
          />
        </label>

        <div class="action-row">
          <button class="button-primary" type="submit" :disabled="isSubmitting">
            {{ isSubmitting ? "Signing in..." : "Sign in" }}
          </button>
        </div>

        <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
      </form>

      <p class="auth-copy">
        Нужен новый employee account?
        <RouterLink class="auth-link" to="/signup">Создать через signup</RouterLink>
      </p>
    </section>
  </div>
</template>
