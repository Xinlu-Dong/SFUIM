<template>
  <div class="waves-bg flex h-full flex-col" style="min-height: 100vh;">
    <TopBar :systemIndex="store.systemIndex" :systemLabel="store.systemLabel" @exit="exit" />

    <div class="relative z-10 flex flex-1 items-center justify-center p-6">
      <div class="w-[720px] max-w-[92vw] rounded-xl bg-white p-10 text-center shadow">
        <div class="text-lg font-semibold">Instructions</div>
        <div class="mt-4 space-y-2 text-sm text-gray-700">
          <p>Please ask questions freely around the given topic/task, up to 10 rounds.</p>
          <p>After each response, please complete the rating in the left panel.</p>
          <p>If you are satisfied, you can end the conversation early and proceed to the next system interaction.</p>
        </div>

        <button class="mt-8 rounded-lg bg-sky-600 px-6 py-2 text-white" @click="goChat">
          Enter Chat
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import "@/assets/waves.css";
import { useRouter } from "vue-router";
import { useStudyStore } from "@/store/study";
import TopBar from "@/components/TopBar.vue";

const router = useRouter();
const store = useStudyStore();

async function goChat() {
  await router.push("/chat");
}

async function exit() {
  // 简单返回封面（真实实验可改为“确认退出”）
  await router.push("/");
}
</script>