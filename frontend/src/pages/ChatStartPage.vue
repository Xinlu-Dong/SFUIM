<template>
  <div class="waves-bg flex h-full flex-col" style="min-height: 100vh;">
    <TopBar :systemIndex="store.systemIndex" :systemLabel="store.systemLabel" @exit="exit" />

    <div class="relative z-10 flex flex-1 items-center justify-center p-6">
      <div class="w-[720px] max-w-[92vw] rounded-xl bg-white p-10 text-center shadow">
        <div class="text-lg font-semibold">Instructions</div>
        <div class="mt-4 space-y-2 text-sm text-gray-700">
          <p>You will interact with four versions of the system during this study.</p>
          <p>For each system, please ask questions freely around the given topic, with up to 10 rounds of conversation.</p>
          <p>After each response, please complete the rating and feedback in the left panel.</p>
          <p>You may end a system early once you feel you have sufficiently understood the topic.</p>
          <p>After finishing all systems, you will complete a short questionnaire.</p>
        </div>

        <button class="mt-8 rounded-lg bg-sky-600 px-6 py-2 text-white" @click="goTopic">
          Continue
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

async function goTopic() {
  await router.push("/topic");
}

async function exit() {
  store.clearSession();
  await router.push("/");
}
</script>