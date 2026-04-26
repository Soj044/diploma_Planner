import { createRouter, createWebHistory } from "vue-router";

import AssignmentsView from "../views/AssignmentsView.vue";
import HomeView from "../views/HomeView.vue";
import NotFoundView from "../views/NotFoundView.vue";
import PlanningView from "../views/PlanningView.vue";
import ReferenceDataView from "../views/ReferenceDataView.vue";
import TasksView from "../views/TasksView.vue";

const routes = [
  {
    path: "/",
    name: "home",
    component: HomeView,
    meta: {
      title: "Frontend Shell",
    },
  },
  {
    path: "/reference-data",
    name: "reference-data",
    component: ReferenceDataView,
    meta: {
      title: "Reference Data",
    },
  },
  {
    path: "/tasks",
    name: "tasks",
    component: TasksView,
    meta: {
      title: "Tasks",
    },
  },
  {
    path: "/planning",
    name: "planning",
    component: PlanningView,
    meta: {
      title: "Planning Runs",
    },
  },
  {
    path: "/assignments",
    name: "assignments",
    component: AssignmentsView,
    meta: {
      title: "Assignments",
    },
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: NotFoundView,
    meta: {
      title: "Not Found",
    },
  },
] as const;

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.afterEach((to) => {
  const pageTitle = typeof to.meta.title === "string" ? to.meta.title : "Workestrator";
  document.title = `${pageTitle} · Workestrator`;
});
