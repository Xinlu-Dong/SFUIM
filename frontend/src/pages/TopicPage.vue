<template>
  <div class="waves-bg flex h-full flex-col" style="min-height: 100vh;">
    <TopBar :systemIndex="store.systemIndex" :systemLabel="store.systemLabel" @exit="exit" />

    <div class="relative z-10 flex flex-1 items-center justify-center p-6">
      <div class="w-[720px] max-w-[92vw] rounded-xl bg-white p-10 text-center shadow">
        <div class="text-sm font-medium text-sky-700">
          System {{ store.systemIndex + 1 }}
        </div>

        <div class="mt-2 text-lg font-semibold">
          Topic for this system
        </div>

        <div class="mt-6 rounded-lg bg-sky-50 px-6 py-5 text-left text-base leading-7 text-gray-800">
          {{ store.currentTopicTitle }}
        </div>

        <div class="mt-4 text-sm text-gray-600">
          Please focus your questions on this topic in the next conversation.
        </div>

        <button class="mt-8 rounded-lg bg-sky-600 px-6 py-2 text-white" @click="goChat">
          Start this system
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import "@/assets/waves.css";
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useStudyStore } from "@/store/study";
import TopBar from "@/components/TopBar.vue";

const router = useRouter();
const store = useStudyStore();

onMounted(() => {
  if (!store.sessionId) {
    router.push("/");
    return;
  }
  if (!store.currentTopicTitle) {
    router.push("/start");
  }
});

async function goChat() {
  await router.push("/chat");
}

async function exit() {
  store.clearSession();
  await router.push("/");
}
</script>