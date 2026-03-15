<template>
  <div class="flex h-full flex-col">
    <div class="min-h-0 flex-1 overflow-auto p-4">
      <div class="mx-auto flex w-full max-w-4xl flex-col gap-3">
        <MessageBubble v-for="m in messages" :key="m.id" :role="m.role" :text="m.text" />
        <div v-if="isSending" class="text-center text-xs text-gray-500">Generating response…</div>
        <div v-if="needFeedback" class="text-center text-xs text-blue-600">This round is complete. Please rate this round on the left before continuing.</div>
        <div v-if="needSwitch" class="text-center text-xs text-red-600">This system phase is complete. Please switch to the next system.</div>
      </div>
    </div>

    <div class="border-t bg-white p-3">
      <div class="mx-auto flex w-full max-w-4xl gap-2">
        <input
          v-model="input"
          class="flex-1 rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-sky-300 disabled:bg-gray-100"
          :disabled="disabled"
          placeholder="Enter your question here…"
          @keydown.enter.prevent="onSend()"
        />
        <button
          class="rounded-lg bg-sky-600 px-4 py-2 text-sm text-white disabled:bg-gray-400"
          :disabled="disabled || input.trim().length === 0"
          @click="onSend()"
        >
          Send
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import MessageBubble from "./MessageBubble.vue";
import type { Msg } from "@/store/study";

const props = defineProps<{
  messages: Msg[];
  disabled: boolean;
  isSending: boolean;
  needFeedback: boolean;
  needSwitch: boolean;
}>();

const emit = defineEmits<{ (e: "send", text: string): void }>();

const input = ref("");

function onSend() {
  const text = input.value.trim();
  if (!text || props.disabled) return;
  emit("send", text);
  input.value = "";
}
</script>