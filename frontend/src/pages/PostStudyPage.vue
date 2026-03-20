<template>
  <div class="min-h-screen bg-slate-50 px-4 py-8">
    <div class="mx-auto max-w-4xl">
      <div class="rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
        <h1 class="text-2xl font-bold text-slate-900">Post-study Questionnaire</h1>
        <p class="mt-2 text-sm text-slate-600">
          Thank you for completing the interaction tasks. Please answer the following questions based on your overall experience.
        </p>

        <div class="mt-8 space-y-8">
          <section>
            <h2 class="text-lg font-semibold text-slate-900">Background Information</h2>

            <div class="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <label class="mb-2 block text-sm font-medium text-slate-800">Age range</label>
                <select v-model="form.age_range" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                  <option value="">Please select</option>
                  <option>18–24</option>
                  <option>25–34</option>
                  <option>35–44</option>
                  <option>45+</option>
                </select>
              </div>

              <div>
                <label class="mb-2 block text-sm font-medium text-slate-800">Gender</label>
                <select v-model="form.gender" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                  <option value="">Please select</option>
                  <option>Prefer not to say</option>
                  <option>Female</option>
                  <option>Male</option>
                  <option>Other</option>
                </select>
              </div>

              <div>
                <label class="mb-2 block text-sm font-medium text-slate-800">Highest level of education completed</label>
                <select v-model="form.education_level" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                  <option value="">Please select</option>
                  <option>Secondary school</option>
                  <option>Undergraduate</option>
                  <option>Postgraduate</option>
                  <option>Other</option>
                </select>
              </div>

              <div>
                <label class="mb-2 block text-sm font-medium text-slate-800">Field of study</label>
                <select v-model="form.field_of_study" class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                  <option value="">Please select</option>
                  <option>Computer Science & Engineering Sciences</option>
                  <option>Natural Science(Biology/Chemistry/Physics/Mathematics...)</option>
                  <option>Health & Medicine</option>
                  <option>Business & Economics</option>
                  <option>Arts & Humanities</option>
                  <option>Law & Political Science</option>
                  <option>Social Sciences</option>
                  <option>Other</option>
                  <option>Not applicable</option>
                </select>
              </div>
            </div>
          </section>

          <section>
            <h2 class="text-lg font-semibold text-slate-900">System Comparison</h2>

            <div class="mt-4 space-y-5">
              <div>
                <label class="mb-2 block text-sm font-medium text-slate-800">
                  Which system did you find easier to understand overall?
                </label>
                <div class="flex flex-wrap gap-4 text-sm text-slate-700">
                  <label v-for="opt in systemOptions" :key="'easy-' + opt" class="flex items-center gap-2">
                    <input v-model="form.easiest_system" type="radio" :value="opt" />
                    <span>{{ opt }}</span>
                  </label>
                </div>
              </div>

              <div>
                <label class="mb-2 block text-sm font-medium text-slate-800">
                  Which system better matched your preferred way of learning?
                </label>
                <div class="flex flex-wrap gap-4 text-sm text-slate-700">
                  <label v-for="opt in systemOptions" :key="'match-' + opt" class="flex items-center gap-2">
                    <input v-model="form.best_learning_match" type="radio" :value="opt" />
                    <span>{{ opt }}</span>
                  </label>
                </div>
              </div>
            </div>
          </section>

          <section>
            <h2 class="text-lg font-semibold text-slate-900">Ratings</h2>

            <div class="mt-4 space-y-6">
              <div>
                <label class="mb-2 block text-sm font-medium text-slate-800">
                  The system adapted its responses to my needs. (1–5)
                </label>
                <div class="flex gap-5 text-sm">
                  <label v-for="n in [1,2,3,4,5]" :key="'adapt-' + n" class="flex items-center gap-2">
                    <input v-model.number="form.adaptation_rating" type="radio" :value="n" />
                    <span>{{ n }}</span>
                  </label>
                </div>
              </div>

              <div>
                <label class="mb-2 block text-sm font-medium text-slate-800">
                  Confidence in understanding the topic after using the system. (1–5)
                </label>
                <div class="flex gap-5 text-sm">
                  <label v-for="n in [1,2,3,4,5]" :key="'confidence-' + n" class="flex items-center gap-2">
                    <input v-model.number="form.confidence_rating" type="radio" :value="n" />
                    <span>{{ n }}</span>
                  </label>
                </div>
              </div>

              <div>
                <label class="mb-2 block text-sm font-medium text-slate-800">
                  Would you use this system again?
                </label>
                <div class="flex flex-wrap gap-4 text-sm">
                  <label class="flex items-center gap-2">
                    <input v-model="form.use_again" type="radio" value="Yes" />
                    <span>Yes</span>
                  </label>
                  <label class="flex items-center gap-2">
                    <input v-model="form.use_again" type="radio" value="No" />
                    <span>No</span>
                  </label>
                  <label class="flex items-center gap-2">
                    <input v-model="form.use_again" type="radio" value="Not sure" />
                    <span>Not sure</span>
                  </label>
                </div>
              </div>
            </div>
          </section>

          <section>
            <h2 class="text-lg font-semibold text-slate-900">Open-ended Feedback</h2>

            <div class="mt-4 space-y-5">
              <div>
                <label class="mb-2 block text-sm font-medium text-slate-800">
                  What aspects of the system did you find most helpful?
                </label>
                <textarea
                  v-model.trim="form.helpful_aspects"
                  rows="5"
                  class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>

              <div>
                <label class="mb-2 block text-sm font-medium text-slate-800">
                  What aspects could be improved?
                </label>
                <textarea
                  v-model.trim="form.improvement_suggestions"
                  rows="5"
                  class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
          </section>
        </div>

        <div
          v-if="errorMsg"
          class="mt-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
        >
          {{ errorMsg }}
        </div>

        <div class="mt-8 flex gap-3">
          <button
            class="rounded-lg border border-slate-300 px-5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            @click="goBack"
          >
            Back
          </button>

          <button
            class="rounded-lg bg-sky-600 px-5 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-60"
            :disabled="submitting"
            @click="handleSubmit"
          >
            {{ submitting ? "Submitting..." : "Submit Questionnaire" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { submitPostStudy } from "@/api/study";
import { useStudyStore } from "@/store/study";

const route = useRoute();
const router = useRouter();
const store = useStudyStore();

const submitting = ref(false);
const errorMsg = ref("");

const systemOptions = [
  "System A",
  "System B",
  "System C",
  "System D",
  "No noticeable difference"
];

const form = reactive({
  age_range: "",
  gender: "",
  education_level: "",
  field_of_study: "",

  easiest_system: "",
  best_learning_match: "",

  adaptation_rating: 0,
  confidence_rating: 0,
  use_again: "",

  helpful_aspects: "",
  improvement_suggestions: ""
});

function validateForm() {
  if (!form.age_range) return "Please select your age range.";
  if (!form.gender) return "Please select your gender.";
  if (!form.education_level) return "Please select your education level.";
  if (!form.field_of_study) return "Please select your field of study.";
  if (!form.easiest_system) return "Please select which system was easier to understand.";
  if (!form.best_learning_match) return "Please select which system better matched your preferred way of learning.";
  if (!form.adaptation_rating) return "Please rate whether the system adapted its responses to your needs.";
  if (!form.confidence_rating) return "Please rate your confidence in understanding the topic.";
  if (!form.use_again) return "Please indicate whether you would use this system again.";
  return "";
}

async function handleSubmit() {
  errorMsg.value = validateForm();
  if (errorMsg.value) return;

  const sessionId =
    (route.query.session_id as string) ||
    store.sessionId ||
    localStorage.getItem("sfuim_session_id") ||
    "";

  if (!sessionId) {
    errorMsg.value = "Missing session ID. Please restart the study.";
    return;
  }

  submitting.value = true;

  try {
    await submitPostStudy(sessionId, {
      age_range: form.age_range,
      gender: form.gender,
      education_level: form.education_level,
      field_of_study: form.field_of_study,
      easiest_system: form.easiest_system,
      best_learning_match: form.best_learning_match,
      adaptation_rating: form.adaptation_rating,
      confidence_rating: form.confidence_rating,
      use_again: form.use_again,
      helpful_aspects: form.helpful_aspects,
      improvement_suggestions: form.improvement_suggestions
    });

    store.clearSession();
    await router.push("/thank-you");
  } catch (e: any) {
    errorMsg.value = `Failed to submit questionnaire: ${e.message}`;
  } finally {
    submitting.value = false;
  }
}

function goBack() {
  router.back();
}
</script>