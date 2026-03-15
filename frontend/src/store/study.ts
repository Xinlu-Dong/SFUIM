import { defineStore } from "pinia";

export type Msg = {
  id: string;
  role: "user" | "assistant";
  text: string;
  ts: number;
};

export type FeedbackDraft = {
  rating: number;
  d_complexity: number;
  d_examples: number;
  d_structure: number;
};

export const useStudyStore = defineStore("study", {
  state: () => ({
    sessionId: "" as string,
    systemLabel: "" as "A" | "B" | "C" | "D" | "",
    systemIndex: 0, // 0/1/2/3 -> 对用户展示为 system 1/2/3/4

    currentTopicId: "" as string,
    currentTopicTitle: "" as string,

    isFinishedAll: false,

    messages: [] as Msg[],
    pendingFeedback: false,
    lastNeedSwitch: false,
    isSending: false,

    feedback: {
      rating: 0,
      d_complexity: 0,
      d_examples: 0,
      d_structure: 0
    } as FeedbackDraft
  }),

  actions: {
    startSession(payload: {
      sessionId: string;
      systemLabel: "A" | "B" | "C" | "D";
      activeConditionIndex: number;
      currentTopicId: string;
      currentTopicTitle: string;
    }) {
      this.sessionId = payload.sessionId;
      this.systemLabel = payload.systemLabel;
      this.systemIndex = payload.activeConditionIndex;
      this.currentTopicId = payload.currentTopicId;
      this.currentTopicTitle = payload.currentTopicTitle;
      this.isFinishedAll = false;

      this.messages = [];
      this.pendingFeedback = false;
      this.lastNeedSwitch = false;
      this.isSending = false;
      this.feedback = { rating: 0, d_complexity: 0, d_examples: 0, d_structure: 0 };
    },

    setCurrentTopic(payload: {
      activeConditionIndex: number;
      currentTopicId: string;
      currentTopicTitle: string;
    }) {
      this.systemIndex = payload.activeConditionIndex;
      this.currentTopicId = payload.currentTopicId;
      this.currentTopicTitle = payload.currentTopicTitle;
    },

    resetConversationForNextSystem() {
      this.messages = [];
      this.pendingFeedback = false;
      this.lastNeedSwitch = false;
      this.isSending = false;
      this.feedback = { rating: 0, d_complexity: 0, d_examples: 0, d_structure: 0 };
    },

    clearSession() {
      this.sessionId = "";
      this.systemLabel = "";
      this.systemIndex = 0;
      this.currentTopicId = "";
      this.currentTopicTitle = "";
      this.isFinishedAll = false;
      this.messages = [];
      this.pendingFeedback = false;
      this.lastNeedSwitch = false;
      this.isSending = false;
      this.feedback = { rating: 0, d_complexity: 0, d_examples: 0, d_structure: 0 };
    }
  }
});