<template>
  <div class="flex items-center justify-between bg-sky-100 px-4 py-2">
    <div class="flex items-center gap-4 text-sm">
      <div class="font-semibold">SFUIM Study</div>
      <div class="text-gray-600">System {{ systemIndex + 1 }}/4</div>
      <div v-if="systemLabel" class="text-gray-600">Label: {{ systemLabel }}</div>
    </div>

    <button class="rounded bg-white px-3 py-1 text-sm shadow hover:bg-gray-50" @click="$emit('exit')">
      Exit
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  systemIndex: number;
  systemLabel: string;
}>();
defineEmits<{ (e: "exit"): void }>();
</script>