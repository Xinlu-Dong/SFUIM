<template>
  <div class="waves-bg flex h-full items-center justify-center" style="min-height: 100vh;">
    <div class="relative z-10 w-[720px] max-w-[92vw] rounded-2xl bg-blue-600 p-10 text-white shadow-2xl ring-4 ring-white/60">
      <div class="text-5xl font-extrabold tracking-widest">SFUIM</div>
      <div class="mt-3 text-4xl font-bold">Four-Factor Interactive System</div>

      <div class="mt-10 flex items-center gap-3">
        <input id="ack" type="checkbox" v-model="ack" class="h-5 w-5" />
        <label for="ack" class="text-lg">Please read the PIS and consent form</label>
      </div>

      <div class="mt-6 flex flex-wrap gap-3">
        <button class="rounded-lg bg-white/15 px-4 py-2 text-sm hover:bg-white/20" @click="openConsent">
          View PIS / Consent Form
        </button>

        <button
          class="rounded-lg bg-white px-5 py-2 text-sm font-semibold text-blue-700 disabled:bg-white/40 disabled:text-white/70"
          :disabled="!ack"
          @click="start"
        >
          Start
        </button>
      </div>

      <div class="mt-3 text-xs text-white/80">
        You must confirm that you have read the PIS and consent form before starting.
      </div>
    </div>

    <Modal v-if="showConsent" title="Participant Information Sheet & Consent" @close="showConsent=false">
      <ConsentText />
      <template #footer>
        <button class="rounded bg-gray-100 px-3 py-2 text-sm" @click="showConsent=false">关闭</button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import Modal from "@/components/Modal.vue";
import ConsentText from "@/pages/ConsentPage.vue";
import { startStudy } from "@/api/study";
import { useStudyStore } from "@/store/study";
import "@/assets/waves.css";

const router = useRouter();
const store = useStudyStore();

const ack = ref(false);
const showConsent = ref(false);

function openConsent() {
  showConsent.value = true;
}

async function start() {
  const res = await startStudy();
  store.sessionId = res.session_id;
  store.systemLabel = res.system_label;
  store.systemIndex = 0;
  store.isFinishedAll = false;
  store.resetConversationForNextSystem();
  await router.push("/start");
}
</script>