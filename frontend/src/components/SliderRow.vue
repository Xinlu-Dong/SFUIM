<template>
  <div class="mt-4">
    <div class="mb-1 flex items-center gap-2">
      <div class="text-sm font-medium text-gray-800">{{ title }}</div>
      <HelpTooltip
        v-if="helpText"
        :title="title"
        :content="helpText"
        :label="`${title} help`"
      />
    </div>

    <div class="relative px-1 pt-6">
      <div
        class="pointer-events-none absolute left-1/2 top-0 -translate-x-1/2 text-[11px] text-gray-500"
      >
        {{ center }}
      </div>

      <input
        type="range"
        min="-1"
        max="1"
        step="0.1"
        :value="modelValue"
        @input="onInput"
        class="w-full"
      />
    </div>

    <div class="mt-1 flex justify-between text-[11px] text-gray-500">
      <span>{{ left }}</span>
      <span>{{ right }}</span>
    </div>

    <div class="mt-1 text-center text-xs font-medium text-gray-700">
      Current value:
      {{ formattedValue }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import HelpTooltip from "./HelpTooltip.vue";

const props = defineProps<{
  title: string;
  left: string;
  center: string;
  right: string;
  modelValue: number;
  helpText?: string;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: number): void;
}>();

function onInput(event: Event) {
  const target = event.target as HTMLInputElement;
  emit("update:modelValue", Number(target.value));
}

const formattedValue = computed(() => {
  const v = Number(props.modelValue.toFixed(1));
  return v > 0 ? `+${v.toFixed(1)}` : v.toFixed(1);
});
</script>