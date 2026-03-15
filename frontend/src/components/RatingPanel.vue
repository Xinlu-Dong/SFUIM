<template>
  <div class="flex h-full flex-col gap-4 p-4">
    <div class="rounded-lg bg-white p-3 shadow">
      <div class="mb-2 text-sm font-semibold">Rating Panel</div>

      <!-- Overall rating -->
      <div class="mb-2 text-xs text-gray-600">Overall Satisfaction (-5 ~ +5)</div>
      <div class="flex items-center gap-2">
        <input
          type="range"
          min="-5"
          max="5"
          step="1"
          v-model.number="local.rating"
          class="w-full"
        />
        <div class="w-10 text-right text-sm font-semibold">
          {{ local.rating > 0 ? `+${local.rating}` : local.rating }}
        </div>
      </div>

      <!-- CES sliders -->
      <div class="mt-4 text-xs text-gray-600">
        Style Preference (continuous feedback from -1.0 to +1.0)
      </div>

      <SliderRow
        title="Complexity"
        left="Simpler"
        center="Just right"
        right="More advanced"
        v-model="local.d_complexity"
      />

      <SliderRow
        title="Examples"
        left="Fewer examples"
        center="Just right"
        right="More examples"
        v-model="local.d_examples"
      />

      <SliderRow
        title="Structure"
        left="Less structured"
        center="Just right"
        right="More structured"
        v-model="local.d_structure"
      />

      <button
        class="mt-4 w-full rounded-lg bg-sky-600 px-3 py-2 text-sm text-white disabled:bg-gray-400"
        :disabled="!canSubmit"
        @click="$emit('submit', { ...local })"
      >
        Submit Feedback
      </button>

      <div class="mt-2 text-xs text-gray-500">
        You must submit feedback on the left rating panel before starting the next round.
      </div>
    </div>

    <button
      class="mt-auto w-full rounded-lg border bg-white px-3 py-3 text-sm shadow hover:bg-gray-50"
      @click="$emit('end')"
    >
      End this System and continue to the Next One.
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import SliderRow from "./SliderRow.vue";
import type { FeedbackDraft } from "@/store/study";

const props = defineProps<{
  modelValue: FeedbackDraft;
  enabled: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: FeedbackDraft): void;
  (e: "submit", v: FeedbackDraft): void;
  (e: "end"): void;
}>();

const local = reactive<FeedbackDraft>({ ...props.modelValue });

watch(
  () => props.modelValue,
  (v) => Object.assign(local, v)
);

watch(
  () => ({ ...local }),
  (v) => emit("update:modelValue", v as FeedbackDraft),
  { deep: true }
);

const canSubmit = computed(() => props.enabled);
</script>