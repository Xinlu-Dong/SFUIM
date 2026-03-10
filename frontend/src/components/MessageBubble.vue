<template>
  <div class="flex" :class="role === 'user' ? 'justify-end' : 'justify-start'">
    <div
      class="max-w-[70%] rounded-2xl px-4 py-3 text-sm leading-6 shadow"
      :class="role === 'user' ? 'bg-sky-600 text-white' : 'bg-white text-gray-900'"
    >
      <pre class="whitespace-pre-wrap font-sans">{{ text }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ role: "user" | "assistant"; text: string }>();
</script>