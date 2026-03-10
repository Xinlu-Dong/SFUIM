import { createRouter, createWebHistory } from "vue-router";
import CoverPage from "@/pages/CoverPage.vue";
import ConsentPage from "@/pages/ConsentPage.vue";
import ChatStartPage from "@/pages/ChatStartPage.vue";
import ChatPage from "@/pages/ChatPage.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: CoverPage },
    { path: "/consent", component: ConsentPage },
    { path: "/start", component: ChatStartPage },
    { path: "/chat", component: ChatPage }
  ]
});