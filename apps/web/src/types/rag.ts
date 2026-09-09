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
  commodity?: string | null;
  province?: string | null;
}

export interface ContactInfo {
  name: string;
  position: string;
  organization: string;
  office: string;
  phone: string;
  email: string;
  how_to_reach: string;
  verified: string;
  scope: string;
}

export interface RagQueryResponse {
  answer: string;
  citations: Citation[];
  analytics_context_used: boolean;
  analytics_scope?: string | null;
  contact?: ContactInfo | null;
}
