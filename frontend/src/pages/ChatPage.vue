<template>
  <div class="flex h-full flex-col" style="min-height: 100vh;">
    <TopBar :systemIndex="store.systemIndex" :systemLabel="store.systemLabel" @exit="exit" />

    <div class="flex flex-1 bg-gray-50">
      <!-- 左侧评分栏 -->
      <div class="w-[320px] shrink-0 border-r bg-sky-100">
        <RatingPanel
          v-model="store.feedback"
          :enabled="store.pendingFeedback"
          @submit="submitFeedback"
          @end="endAndNext"
        />
      </div>

      <!-- 右侧聊天区 -->
      <div class="flex-1">
        <ChatWindow
          :messages="store.messages"
          :disabled="store.isSending || store.pendingFeedback || store.lastNeedSwitch || store.isFinishedAll"
          :isSending="store.isSending"
          :needFeedback="store.pendingFeedback"
          :needSwitch="store.lastNeedSwitch"
          @send="send"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { nanoid } from "./_nanoid";
import TopBar from "@/components/TopBar.vue";
import RatingPanel from "@/components/RatingPanel.vue";
import ChatWindow from "@/components/ChatWindow.vue";
import { useStudyStore } from "@/store/study";
import { sendChat, sendFeedback, nextSystem } from "@/api/study";

const router = useRouter();
const store = useStudyStore();

function ensureSession() {
  if (!store.sessionId) {
    router.push("/");
    return false;
  }
  return true;
}

async function send(text: string) {
  if (!ensureSession()) return;

  // append user msg
  store.messages.push({ id: nanoid(), role: "user", text, ts: Date.now() });

  store.isSending = true;
  store.lastNeedSwitch = false;

  try {
    const res = await sendChat(store.sessionId, text);

    store.messages.push({ id: nanoid(), role: "assistant", text: res.answer, ts: Date.now() });

    // ✅ 收到答复后：必须反馈
    store.pendingFeedback = true;

    // 后端提示需要切换（达到 10 轮）
    store.lastNeedSwitch = res.need_switch || res.is_finished;

    if (res.is_finished) {
      store.isFinishedAll = true;
    }
  } catch (e: any) {
    store.messages.push({
      id: nanoid(),
      role: "assistant",
      text: `Request failed: ${e.message}`,
      ts: Date.now()
    });
  } finally {
    store.isSending = false;
  }
}

async function submitFeedback(payload: any) {
  if (!ensureSession()) return;
  if (!store.pendingFeedback) return;

  try {
    await sendFeedback(store.sessionId, payload);
    store.pendingFeedback = false;
  } catch (e: any) {
    alert(`Submit feedback failed: ${e.message}`);
  }
}

async function endAndNext() {
  if (!ensureSession()) return;

  // 如果还没反馈，提醒先反馈（避免你后端日志缺字段）
  if (store.pendingFeedback) {
    alert("Please submit your feedback for this round before ending the conversation and proceeding to the next system.");
    return;
  }

  try {
    const res = await nextSystem(store.sessionId);

    if (res.is_finished) {
      store.isFinishedAll = true;
      alert("This study is complete. Thank you for your participation!");
      await router.push("/");
      return;
    }

    store.systemIndex = Math.min(store.systemIndex + 1, 3);
    store.resetConversationForNextSystem();
    await router.push("/start");
  } catch (e: any) {
    alert(`Failed to switch system: ${e.message}`);
  }
}

async function exit() {
  await router.push("/");
}
</script>

<!-- 小工具：生成 message id -->
<script lang="ts">
export {};
</script>