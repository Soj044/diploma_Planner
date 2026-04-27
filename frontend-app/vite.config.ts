import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const coreProxyTarget = env.VITE_CORE_SERVICE_PROXY_TARGET || "http://localhost:8000";
  const plannerProxyTarget = env.VITE_PLANNER_SERVICE_PROXY_TARGET || "http://localhost:8001";

  return {
    plugins: [vue()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/core-api": {
          target: coreProxyTarget,
          changeOrigin: true,
        },
        "/planner-api": {
          target: plannerProxyTarget,
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: "0.0.0.0",
      port: 4173,
    },
  };
});
