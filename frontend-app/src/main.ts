import { createApp } from "vue";

import App from "./App.vue";
import { router } from "./router";
import { bootstrapAuth } from "./services/auth-service";
import "./styles.css";

async function bootstrap() {
  await bootstrapAuth();

  const app = createApp(App);
  app.use(router);
  await router.isReady();
  app.mount("#app");
}

void bootstrap();
