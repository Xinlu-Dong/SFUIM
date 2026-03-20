<template>
  <div class="min-h-screen bg-slate-50 px-4 py-8">
    <div class="mx-auto max-w-4xl">
      <div class="rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
        <h1 class="text-2xl font-bold text-slate-900">Participant Information and Consent</h1>
        <p class="mt-2 text-sm text-slate-600">
          SFUIM User Study — University of Southampton
        </p>

        <section class="mt-8 space-y-4 text-sm leading-7 text-slate-700">
          <h2 class="text-lg font-semibold text-slate-900">Study Summary</h2>

          <p>
            This study investigates how personalised prompt adaptation can improve user understanding
            and satisfaction when interacting with an AI-based question answering system.
          </p>

          <ul class="list-disc space-y-2 pl-5">
            <li>You will interact with four versions of the system.</li>
            <li>For each system, you may have up to 10 turns of conversation.</li>
            <li>After each response, you will provide brief ratings and feedback.</li>
            <li>After finishing all four systems, you will complete a short post-study questionnaire.</li>
            <li>The study takes approximately 40–60 minutes in total.</li>
            <li>You will not be told which system version you are using at any given time.</li>
            <li>No audio or video recording will be used.</li>
            <li>Your responses will be collected anonymously and analysed in aggregated form only.</li>
            <li>You may withdraw at any time without giving a reason. However, because the study is anonymous,
              it will not be possible to remove your data after submission.</li>
            <li>You will receive £5 compensation for your time. This is not dependent on completion.</li>
          </ul>

          <p>
            If you would like to read the full official documents, please open the files below before continuing.
          </p>

          <div class="flex flex-wrap gap-3 pt-1">
            <a
              href="/docs/pis.pdf"
              target="_blank"
              rel="noopener"
              class="rounded-lg border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-700 hover:bg-sky-100"
            >
              View Participant Information Sheet
            </a>

            <a
              href="/docs/consent.pdf"
              target="_blank"
              rel="noopener"
              class="rounded-lg border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-700 hover:bg-sky-100"
            >
              View Consent Form
            </a>
          </div>
        </section>

        <section class="mt-10">
          <h2 class="text-lg font-semibold text-slate-900">Electronic Consent</h2>
          <p class="mt-2 text-sm leading-6 text-slate-700">
            Please enter your initials and confirm all statements below before proceeding.
          </p>

          <div class="mt-5 max-w-xs">
            <label class="mb-2 block text-sm font-medium text-slate-800">
              Participant initials
            </label>
            <input
              v-model.trim="initials"
              type="text"
              maxlength="12"
              placeholder="e.g. XD"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-sky-500"
            />
          </div>

          <div class="mt-6 space-y-4">
            <label class="flex items-start gap-3 rounded-xl border border-slate-200 p-4">
              <input v-model="checks.c1" type="checkbox" class="mt-1" />
              <span class="text-sm leading-6 text-slate-700">
                I confirm that I have read the Participant Information Sheet version 2.0, dated 25/02/2026,
                explaining the study above and I understand what is expected of me.
              </span>
            </label>

            <label class="flex items-start gap-3 rounded-xl border border-slate-200 p-4">
              <input v-model="checks.c2" type="checkbox" class="mt-1" />
              <span class="text-sm leading-6 text-slate-700">
                I was given the opportunity to consider the information, ask questions about the study,
                and all my questions have been answered to my satisfaction.
              </span>
            </label>

            <label class="flex items-start gap-3 rounded-xl border border-slate-200 p-4">
              <input v-model="checks.c3" type="checkbox" class="mt-1" />
              <span class="text-sm leading-6 text-slate-700">
                I agree to take part in this study and understand that data collected during this research
                project will be used for the purpose of this study.
              </span>
            </label>

            <label class="flex items-start gap-3 rounded-xl border border-slate-200 p-4">
              <input v-model="checks.c4" type="checkbox" class="mt-1" />
              <span class="text-sm leading-6 text-slate-700">
                I understand that my participation is voluntary and that I am free to withdraw from this
                study at any time without giving a reason.
              </span>
            </label>
          </div>

          <div
            v-if="errorMsg"
            class="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
          >
            {{ errorMsg }}
          </div>

          <div class="mt-8 flex flex-wrap gap-3">
            <button
              class="rounded-lg border border-slate-300 px-5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
              @click="goBack"
            >
              Back
            </button>

            <button
              class="rounded-lg bg-sky-600 px-5 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-60"
              :disabled="submitting"
              @click="handleContinue"
            >
              {{ submitting ? "Starting..." : "Continue" }}
            </button>
          </div>

          <div class="mt-8 text-xs leading-6 text-slate-500">
            <p>If you have questions, please contact: Xinlu Dong – xd3g23@soton.ac.uk</p>
            <p>
              If you remain unhappy or have a complaint about any part of the study, you may contact the
              Head of Research Ethics and Governance, University of Southampton.
            </p>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { startStudy } from "@/api/study";
import { useStudyStore } from "@/store/study";

const store = useStudyStore();
const router = useRouter();

const initials = ref("");
const errorMsg = ref("");

const checks = reactive({
  c1: false,
  c2: false,
  c3: false,
  c4: false
});

const submitting = ref(false);

async function handleContinue() {
  if (submitting.value) return;

  if (!initials.value.trim()) {
    errorMsg.value = "Please enter your initials before continuing.";
    return;
  }

  if (!(checks.c1 && checks.c2 && checks.c3 && checks.c4)) {
    errorMsg.value = "Please confirm all mandatory consent statements before continuing.";
    return;
  }

  errorMsg.value = "";
  submitting.value = true;

  try {
    localStorage.setItem(
      "sfuim_consent",
      JSON.stringify({
        initials: initials.value.trim(),
        consented: true,
        consentedAt: new Date().toISOString()
      })
    );

    const res = await startStudy();

    store.startSession({
      sessionId: res.session_id,
      systemLabel: res.system_label,
      activeConditionIndex: res.active_condition_index,
      currentTopicId: res.current_topic_id,
      currentTopicTitle: res.current_topic_title
    });

    await router.push("/start");
  } catch (e: any) {
    errorMsg.value = e?.message
      ? `Failed to start the study: ${e.message}`
      : "Failed to start the study. Please try again.";
  } finally {
    submitting.value = false;
  }
}

function goBack() {
  localStorage.removeItem("sfuim_consent");
  router.push("/");
}

</script>