import { createRouter, createWebHistory } from "vue-router";

import AppShell from "../components/AppShell.vue";
import { bootstrapAuth, hasRole, isAuthenticated } from "../services/auth-service";
import AssignmentsView from "../views/AssignmentsView.vue";
import HomeView from "../views/HomeView.vue";
import LoginView from "../views/LoginView.vue";
import MyLeavesView from "../views/MyLeavesView.vue";
import MyScheduleView from "../views/MyScheduleView.vue";
import NotFoundView from "../views/NotFoundView.vue";
import PlanningView from "../views/PlanningView.vue";
import ReferenceDataView from "../views/ReferenceDataView.vue";
import SignupView from "../views/SignupView.vue";
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
        name: "home",
        component: HomeView,
        meta: {
          title: "Frontend Shell",
          requiresAuth: true,
        },
      },
      {
        path: "reference-data",
        name: "reference-data",
        component: ReferenceDataView,
        meta: {
          title: "Reference Data",
          requiresAuth: true,
          allowedRoles: ["admin", "manager"],
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
        path: "my-schedule",
        name: "my-schedule",
        component: MyScheduleView,
        meta: {
          title: "My Schedule",
          requiresAuth: true,
          allowedRoles: ["employee"],
        },
      },
      {
        path: "my-leaves",
        name: "my-leaves",
        component: MyLeavesView,
        meta: {
          title: "My Leaves",
          requiresAuth: true,
          allowedRoles: ["employee"],
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
    return { name: "home" };
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
    return { name: "home" };
  }

  return true;
});

router.afterEach((to) => {
  const pageTitle = typeof to.meta.title === "string" ? to.meta.title : "Workestrator";
  document.title = `${pageTitle} · Workestrator`;
});
