export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface Citation {
  doc_id: string;
  doc_title: string;
  page_start: number;
  page_end: number;
}

export interface RagQueryRequest {
  question: string;
  history: ChatMessage[];
}

export interface RagQueryResponse {
  answer: string;
  citations: Citation[];
}
