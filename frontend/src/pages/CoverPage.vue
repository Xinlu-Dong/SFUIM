<template>
  <div class="waves-bg flex h-full items-center justify-center" style="min-height: 100vh;">
    <div class="relative z-10 w-[720px] max-w-[92vw] rounded-2xl bg-blue-600 p-10 text-white shadow-2xl ring-4 ring-white/60">
      <div class="text-5xl font-extrabold tracking-widest">SFUIM</div>
      <div class="mt-3 text-4xl font-bold">Four-Factor Interactive System</div>

      <div class="mt-10 space-y-3 text-white/90">
        <p class="text-lg">
          Please read the Participant Information Sheet and Consent Form before starting the study.
        </p>
        <p class="text-sm text-white/80">
          On the next page, you will be able to view the study information and provide your electronic consent before the study begins.
        </p>
      </div>

      <div class="mt-8">
        <button
          class="rounded-lg bg-white px-5 py-2 text-sm font-semibold text-blue-700 hover:bg-white/90"
          @click="goConsent"
        >
          View PIS / Consent Form
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import "@/assets/waves.css";

const router = useRouter();

async function goConsent() {
  await router.push("/consent");
}
</script>