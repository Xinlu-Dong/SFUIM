import { createRouter, createWebHistory } from "vue-router";
import CoverPage from "@/pages/CoverPage.vue";
import ConsentPage from "@/pages/ConsentPage.vue";
import ChatStartPage from "@/pages/ChatStartPage.vue";
import TopicPage from "@/pages/TopicPage.vue";
import ChatPage from "@/pages/ChatPage.vue";
import PostStudyPage from "@/pages/PostStudyPage.vue";
import ThankPage from "@/pages/ThankPage.vue";


export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: CoverPage },
    { path: "/consent", component: ConsentPage },
    { path: "/start", component: ChatStartPage }, // Instructions
    { path: "/topic", component: TopicPage },     // NEW
    { path: "/chat", component: ChatPage },
    { path: "/post-study", component: PostStudyPage },
    { path: "/thank-you", component: ThankPage }
  ]
});