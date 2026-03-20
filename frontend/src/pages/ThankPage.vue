<template>
  <div class="min-h-screen bg-slate-50 px-4 py-8">
    <div class="mx-auto max-w-2xl">
      <div class="rounded-2xl bg-white p-10 text-center shadow-sm ring-1 ring-slate-200">
        <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
          <span class="text-3xl">✓</span>
        </div>

        <h1 class="mt-6 text-2xl font-bold text-slate-900">
          Thank you for your participation
        </h1>

        <p class="mt-4 text-sm leading-7 text-slate-700">
          You have successfully completed the study and submitted the final questionnaire.
        </p>

        <p class="mt-3 text-sm leading-7 text-slate-700">
          Your responses have been recorded anonymously and will be used only for academic research purposes.
        </p>

        <p class="mt-3 text-sm leading-7 text-slate-700">
          If compensation is being provided, the researcher will arrange it according to the study instructions.
        </p>

        <div class="mt-8">
          <button
            class="rounded-lg bg-sky-600 px-5 py-2 text-sm font-medium text-white hover:bg-sky-700"
            @click="goHome"
          >
            Return to Home
          </button>
        </div>

        <p class="mt-8 text-xs leading-6 text-slate-500">
          If you have any questions about this study, please contact Xinlu Dong.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

function goHome() {
  router.push("/");
}
</script>