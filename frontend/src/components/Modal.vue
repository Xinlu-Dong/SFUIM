<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="$emit('close')">
    <div class="w-full max-w-2xl rounded-xl bg-white shadow-xl">
      <div class="flex items-center justify-between border-b px-5 py-3">
        <div class="font-semibold">{{ title }}</div>
        <button class="rounded px-2 py-1 hover:bg-gray-100" @click="$emit('close')">✕</button>
      </div>

      <div class="max-h-[70vh] overflow-auto px-5 py-4">
        <slot />
      </div>

      <div class="flex items-center justify-end gap-2 border-t px-5 py-3">
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string }>();
defineEmits<{ (e: "close"): void }>();
</script>