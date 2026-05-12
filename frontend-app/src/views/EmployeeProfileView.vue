<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { coreService } from "../services/core-service";
import { describeRequestError } from "../services/http";
import type { Department, Employee, EmployeeSkill, Skill } from "../types/api";

const route = useRoute();

const employee = ref<Employee | null>(null);
const departments = ref<Department[]>([]);
const skills = ref<Skill[]>([]);
const employeeSkills = ref<EmployeeSkill[]>([]);
const isLoading = ref(false);
const errorMessage = ref("");

const employeeId = computed(() => {
  const numericId = Number(route.params.id);
  return Number.isInteger(numericId) && numericId > 0 ? numericId : null;
});

const departmentNameById = computed(() => {
  return new Map(departments.value.map((department) => [department.id, department.name]));
});

const skillNameById = computed(() => {
  return new Map(skills.value.map((skill) => [skill.id, skill.name]));
});

const employeeSkillRows = computed(() => {
  if (employeeId.value === null) {
    return [];
  }

  return employeeSkills.value
    .filter((entry) => entry.employee === employeeId.value)
    .sort((left, right) => {
      if (left.level !== right.level) {
        return right.level - left.level;
      }
      const leftName = skillNameById.value.get(left.skill) || "";
      const rightName = skillNameById.value.get(right.skill) || "";
      return leftName.localeCompare(rightName);
    });
});

async function load() {
  if (employeeId.value === null) {
    employee.value = null;
    errorMessage.value = "Employee profile link is invalid.";
    return;
  }

  isLoading.value = true;
  errorMessage.value = "";

  try {
    const [employeeRow, departmentRows, skillRows, employeeSkillRows] = await Promise.all([
      coreService.getEmployee(employeeId.value),
      coreService.listDepartments(),
      coreService.listSkills(),
      coreService.listEmployeeSkills(),
    ]);
    employee.value = employeeRow;
    departments.value = departmentRows;
    skills.value = skillRows;
    employeeSkills.value = employeeSkillRows;
  } catch (error: unknown) {
    employee.value = null;
    errorMessage.value = describeRequestError(error);
  } finally {
    isLoading.value = false;
  }
}

watch(
  () => route.params.id,
  () => {
    void load();
  },
);

onMounted(load);
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <div class="editor-header">
        <div>
          <p class="eyebrow">Employee Profile</p>
          <h3 class="page-title">{{ employee?.full_name || "Employee profile" }}</h3>
          <p class="page-description">
            Review the employee record and current skill map without leaving the department directory flow.
          </p>
        </div>
        <RouterLink class="button-secondary" to="/departments">Back to departments</RouterLink>
      </div>
    </section>

    <p v-if="errorMessage" class="status-banner is-error">{{ errorMessage }}</p>
    <p v-else-if="isLoading" class="resource-copy">Loading employee profile and skills...</p>
    <p v-else-if="!employee" class="empty-state">Employee profile is unavailable.</p>

    <template v-else>
      <section class="page-card">
        <div class="grid-two">
          <div class="records-card">
            <p class="section-caption">Profile details</p>
            <ul class="key-value-list">
              <li class="key-value-item">
                <span class="key-label">Department</span>
                <span class="key-value">
                  {{
                    employee.department === null
                      ? "Unassigned"
                      : departmentNameById.get(employee.department) || `#${employee.department}`
                  }}
                </span>
              </li>
              <li class="key-value-item">
                <span class="key-label">Position</span>
                <span class="key-value">{{ employee.position_name || "Not set" }}</span>
              </li>
              <li class="key-value-item">
                <span class="key-label">Employment type</span>
                <span class="key-value">{{ employee.employment_type }}</span>
              </li>
              <li class="key-value-item">
                <span class="key-label">Weekly capacity</span>
                <span class="key-value">{{ employee.weekly_capacity_hours }}h</span>
              </li>
              <li class="key-value-item">
                <span class="key-label">Timezone</span>
                <span class="key-value">{{ employee.timezone }}</span>
              </li>
              <li class="key-value-item">
                <span class="key-label">Hire date</span>
                <span class="key-value">{{ employee.hire_date || "Not set" }}</span>
              </li>
              <li class="key-value-item">
                <span class="key-label">Active</span>
                <span class="key-value">{{ employee.is_active ? "Yes" : "No" }}</span>
              </li>
            </ul>
          </div>

          <div class="records-card">
            <div class="editor-header">
              <div>
                <p class="section-caption">Skills</p>
                <p class="resource-copy">Skills reflect the current employee capability map used across planning flows.</p>
              </div>
              <span class="pill">{{ employeeSkillRows.length }} skills</span>
            </div>

            <p v-if="employeeSkillRows.length === 0" class="empty-state">No skills are assigned to this employee yet.</p>
            <ul v-else class="resource-list">
              <li v-for="entry in employeeSkillRows" :key="entry.id" class="resource-item">
                <div class="resource-heading">
                  <p class="resource-label">{{ skillNameById.get(entry.skill) || `Skill #${entry.skill}` }}</p>
                  <span class="pill">Level {{ entry.level }}</span>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
