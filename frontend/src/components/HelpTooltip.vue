<template>
  <div
    class="relative inline-flex items-center"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
  >
    <button
      type="button"
      class="inline-flex h-4 w-4 items-center justify-center rounded-full border border-sky-400 bg-white text-[10px] font-bold text-sky-600 hover:bg-sky-50 focus:outline-none focus:ring-2 focus:ring-sky-300"
      @click.stop="togglePinned"
      :aria-label="label"
      :title="label"
    >
      i
    </button>

    <div
      v-if="visible"
      class="absolute left-1/2 top-full z-50 mt-2 w-64 -translate-x-1/2 rounded-lg border border-gray-200 bg-white p-3 text-left text-xs leading-5 text-gray-700 shadow-lg"
      @click.stop
    >
      <div v-if="title" class="mb-1 text-sm font-semibold text-gray-800">
        {{ title }}
      </div>
      <div class="whitespace-pre-line">
        {{ content }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from "vue";

const props = defineProps<{
  title?: string;
  content: string;
  label?: string;
}>();

const hovering = ref(false);
const pinned = ref(false);

const visible = computed(() => hovering.value || pinned.value);

function onEnter() {
  hovering.value = true;
}

function onLeave() {
  hovering.value = false;
}

function togglePinned() {
  pinned.value = !pinned.value;
}

function handleDocumentClick() {
  pinned.value = false;
}

onMounted(() => {
  document.addEventListener("click", handleDocumentClick);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick);
});
</script>