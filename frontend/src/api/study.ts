import { http } from "./http";

export type StartStudyResponse = {
  session_id: string;
  system_label: "A" | "B" | "C" | "D";
};

export type ChatResponse = {
  answer: string;
  turn_index: number;
  active_condition?: string | null; // 前端不展示
  turn_in_condition: number;
  need_switch: boolean;
  is_finished: boolean;
};

export type NextResponse = {
  ok: boolean;
  is_finished: boolean;
  active_condition?: string | null;
  active_condition_index: number;
};

export async function startStudy(participantId?: string): Promise<StartStudyResponse> {
  const res = await http.post<StartStudyResponse>("/study/start", {
    participant_id: participantId ?? null
  });
  return res.data;
}

export async function sendChat(sessionId: string, message: string): Promise<ChatResponse> {
  const res = await http.post<ChatResponse>(`/study/${sessionId}/chat`, { message });
  return res.data;
}

export async function sendFeedback(
  sessionId: string,
  payload: { rating: number; d_complexity: number; d_examples: number; d_structure: number }
): Promise<{ ok: boolean }> {
  const res = await http.post(`/study/${sessionId}/feedback`, payload);
  return res.data;
}

export async function nextSystem(sessionId: string): Promise<NextResponse> {
  const res = await http.post<NextResponse>(`/study/${sessionId}/next`, {});
  return res.data;
}