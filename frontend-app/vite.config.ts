import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const coreProxyTarget = env.VITE_CORE_SERVICE_PROXY_TARGET || "http://localhost:8000";
  const plannerProxyTarget = env.VITE_PLANNER_SERVICE_PROXY_TARGET || "http://localhost:8001";
  const aiProxyTarget = env.VITE_AI_SERVICE_PROXY_TARGET || "http://localhost:8002";

  return {
    plugins: [vue()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/api": {
          target: coreProxyTarget,
          changeOrigin: true,
        },
        "/planner-api": {
          target: plannerProxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/planner-api/, ""),
        },
        "/ai-api": {
          target: aiProxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/ai-api/, ""),
        },
      },
    },
    preview: {
      host: "0.0.0.0",
      port: 4173,
    },
  };
});
