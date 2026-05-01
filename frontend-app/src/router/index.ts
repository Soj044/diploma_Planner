import { createRouter, createWebHistory } from "vue-router";

import AppShell from "../components/AppShell.vue";
import { bootstrapAuth, hasRole, isAuthenticated } from "../services/auth-service";
import AdminView from "../views/AdminView.vue";
import AssignmentsView from "../views/AssignmentsView.vue";
import DepartmentsView from "../views/DepartmentsView.vue";
import LeavesView from "../views/LeavesView.vue";
import LoginView from "../views/LoginView.vue";
import NotFoundView from "../views/NotFoundView.vue";
import PlanningView from "../views/PlanningView.vue";
import ProfileView from "../views/ProfileView.vue";
import ScheduleView from "../views/ScheduleView.vue";
import SignupView from "../views/SignupView.vue";
import TaskCreateView from "../views/TaskCreateView.vue";
import TasksView from "../views/TasksView.vue";

const routes = [
  {
    path: "/login",
    name: "login",
    component: LoginView,
    meta: {
      title: "Sign In",
      guestOnly: true,
    },
  },
  {
    path: "/signup",
    name: "signup",
    component: SignupView,
    meta: {
      title: "Sign Up",
      guestOnly: true,
    },
  },
  {
    path: "/",
    component: AppShell,
    meta: {
      requiresAuth: true,
    },
    children: [
      {
        path: "",
        redirect: {
          name: "tasks",
        },
      },
      {
        path: "tasks",
        name: "tasks",
        component: TasksView,
        meta: {
          title: "Tasks",
          requiresAuth: true,
        },
      },
      {
        path: "tasks/new",
        name: "task-create",
        component: TaskCreateView,
        meta: {
          title: "Create Task",
          requiresAuth: true,
          allowedRoles: ["admin", "manager"],
        },
      },
      {
        path: "schedule",
        name: "schedule",
        component: ScheduleView,
        meta: {
          title: "Schedule",
          requiresAuth: true,
        },
      },
      {
        path: "leaves",
        name: "leaves",
        component: LeavesView,
        meta: {
          title: "Leaves",
          requiresAuth: true,
        },
      },
      {
        path: "departments",
        name: "departments",
        component: DepartmentsView,
        meta: {
          title: "Departments",
          requiresAuth: true,
        },
      },
      {
        path: "profile",
        name: "profile",
        component: ProfileView,
        meta: {
          title: "Profile",
          requiresAuth: true,
        },
      },
      {
        path: "admin",
        name: "admin",
        component: AdminView,
        meta: {
          title: "Admin",
          requiresAuth: true,
          allowedRoles: ["admin"],
        },
      },
      {
        path: "planning",
        name: "planning",
        component: PlanningView,
        meta: {
          title: "Planning Runs",
          requiresAuth: true,
          allowedRoles: ["admin", "manager"],
        },
      },
      {
        path: "assignments",
        name: "assignments",
        component: AssignmentsView,
        meta: {
          title: "Assignments",
          requiresAuth: true,
          allowedRoles: ["admin", "manager"],
        },
      },
      {
        path: "reference-data",
        name: "reference-data-legacy",
        redirect: {
          name: "admin",
        },
        meta: {
          title: "Admin",
          requiresAuth: true,
        },
      },
      {
        path: "my-schedule",
        name: "my-schedule-legacy",
        redirect: {
          name: "schedule",
        },
        meta: {
          title: "Schedule",
          requiresAuth: true,
        },
      },
      {
        path: "my-leaves",
        name: "my-leaves-legacy",
        redirect: {
          name: "leaves",
        },
        meta: {
          title: "Leaves",
          requiresAuth: true,
        },
      },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: NotFoundView,
    meta: {
      title: "Not Found",
    },
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  await bootstrapAuth();

  if (to.meta.guestOnly && isAuthenticated()) {
    return { name: "tasks" };
  }

  if (to.meta.requiresAuth && !isAuthenticated()) {
    return {
      name: "login",
      query: {
        redirect: to.fullPath,
      },
    };
  }

  const allowedRoles = Array.isArray(to.meta.allowedRoles) ? (to.meta.allowedRoles as string[]) : null;
  if (allowedRoles && !hasRole(allowedRoles)) {
    return { name: "tasks" };
  }

  return true;
});

router.afterEach((to) => {
  const pageTitle = typeof to.meta.title === "string" ? to.meta.title : "Workestrator";
  document.title = `${pageTitle} · Workestrator`;
});
