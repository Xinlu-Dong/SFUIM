<template>
  <div class="mt-3">
    <div class="mb-1 text-xs font-semibold">{{ title }}</div>
    <div class="grid grid-cols-3 gap-2">
      <button
        type="button"
        class="rounded border px-2 py-2 text-xs"
        :class="modelValue === -1 ? 'bg-sky-50 border-sky-400' : 'bg-white'"
        @click="$emit('update:modelValue', -1)"
      >
        {{ left }}
      </button>

      <button
        type="button"
        class="rounded border px-2 py-2 text-xs"
        :class="modelValue === 0 ? 'bg-sky-50 border-sky-400' : 'bg-white'"
        @click="$emit('update:modelValue', 0)"
      >
        {{ mid }}
      </button>

      <button
        type="button"
        class="rounded border px-2 py-2 text-xs"
        :class="modelValue === 1 ? 'bg-sky-50 border-sky-400' : 'bg-white'"
        @click="$emit('update:modelValue', 1)"
      >
        {{ right }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  left: string;
  mid: string;
  right: string;
  modelValue: -1 | 0 | 1;
}>();

defineEmits<{
  (e: "update:modelValue", v: -1 | 0 | 1): void;
}>();
</script>