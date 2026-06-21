export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface SessionEntry {
  uuid: string;
  preview: string;
  created_at: string;
}

export interface SessionHistoryResponse {
  session_uuid: string;
  messages: Message[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  email: string;
}
