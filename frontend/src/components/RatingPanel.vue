<template>
  <div class="flex h-full flex-col gap-4 p-4">
    <div class="rounded-lg bg-white p-3 shadow">
      <div class="mb-2 flex items-center gap-2">
        <div class="text-sm font-semibold">Rating Panel</div>
        <HelpTooltip
          title="How to use this panel"
          content="After each answer, please give one overall satisfaction rating and adjust the three style sliders if you want the next answer to be different. You must submit feedback before continuing."
          label="Rating panel help"
        />
      </div>

      <!-- First-time lightweight guidance -->
      <div class="mb-3 rounded-md bg-sky-50 px-3 py-2 text-xs text-sky-700">
        Hover over or click the small info icons if you are unsure what each rating means.
      </div>

      <!-- Overall rating -->
      <div class="mb-2 flex items-center gap-2 text-xs text-gray-600">
        <span>Overall Satisfaction (-5 ~ +5)</span>
        <HelpTooltip
          title="Overall Satisfaction"
          content="Use this to rate the answer as a whole.
-5 means the answer was very unhelpful for your learning.
0 means neutral or just acceptable.
+5 means the answer matched your needs very well."
          label="Overall satisfaction help"
        />
      </div>

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
      <div class="mt-4 flex items-center gap-2 text-xs text-gray-600">
        <span>Style Preference (continuous feedback from -1.0 to +1.0)</span>
        <HelpTooltip
          title="Style Preference"
          content="These sliders tell the system how you want the next answer to change.
Negative values mean 'less of this'.
Positive values mean 'more of this'.
0 means the current answer felt about right on that dimension."
          label="Style preference help"
        />
      </div>

      <SliderRow
        title="Complexity"
        left="Simpler"
        center="Just right"
        right="More technical"
        v-model="local.d_complexity"
        helpText="Move left if you want simpler explanations with less jargon and less technical depth. Move right if you want deeper, more advanced, or more technical explanations."
      />

      <SliderRow
        title="Examples"
        left="Fewer examples"
        center="Just right"
        right="More examples"
        v-model="local.d_examples"
        helpText="Move left if you want fewer examples or a more direct explanation. Move right if you want more examples, comparisons, or illustrations."
      />

      <SliderRow
        title="Structure"
        left="More natural"
        center="Just right"
        right="More structured"
        v-model="local.d_structure"
        helpText="Move left if you prefer a more natural paragraph style. Move right if you prefer clearer organisation, such as headings, bullet points, or step-by-step structure."
      />

      <div class="mt-4 flex items-center gap-2">
        <button
          class="w-full rounded-lg bg-sky-600 px-3 py-2 text-sm text-white disabled:bg-gray-400"
          :disabled="!canSubmit"
          @click="$emit('submit', { ...local })"
        >
          Submit Feedback
        </button>
        <HelpTooltip
          title="Submit Feedback"
          content="Click this after setting your overall rating and style preferences. The system will use this feedback to adapt the next answer."
          label="Submit feedback help"
        />
      </div>

      <div class="mt-2 text-xs text-gray-500">
        You must submit feedback on the left rating panel before starting the next round.
      </div>
    </div>

    <div class="mt-auto flex items-center gap-2">
      <button
        class="w-full rounded-lg border bg-white px-3 py-3 text-sm shadow hover:bg-gray-50"
        @click="$emit('end')"
      >
        End this System and continue to the Next One.
      </button>
      <HelpTooltip
        title="End this System"
        content="Use this when you want to stop interacting with the current system and move to the next one. You still need to submit feedback for the latest answer before continuing."
        label="End system help"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import SliderRow from "./SliderRow.vue";
import HelpTooltip from "./HelpTooltip.vue";
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