import { defineStore } from "pinia";

export type Msg = {
  id: string;
  role: "user" | "assistant";
  text: string;
  ts: number;
};

export type FeedbackDraft = {
  rating: number;          // -5..5
  d_complexity: -1 | 0 | 1;
  d_examples: -1 | 0 | 1;
  d_structure: -1 | 0 | 1;
};

export const useStudyStore = defineStore("study", {
  state: () => ({
    sessionId: "" as string,
    systemLabel: "" as "A" | "B" | "C" | "D" | "",   // 对应后端分配的系统标签
    systemIndex: 0,             // 0/1/2/3 对应 系统1/2/3/4（对用户展示）
    isFinishedAll: false,

    messages: [] as Msg[],
    pendingFeedback: false,     // ✅ 收到回答后必须先反馈
    lastNeedSwitch: false,      // ✅ 后端提示 need_switch
    isSending: false,

    feedback: {
      rating: 0,
      d_complexity: 0,
      d_examples: 0,
      d_structure: 0
    } as FeedbackDraft
  }),

  actions: {
    resetConversationForNextSystem() {
      this.messages = [];
      this.pendingFeedback = false;
      this.lastNeedSwitch = false;
      this.isSending = false;
      this.feedback = { rating: 0, d_complexity: 0, d_examples: 0, d_structure: 0 };
    }
  }
});