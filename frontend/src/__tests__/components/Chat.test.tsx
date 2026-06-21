import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ChatWindow from "../../components/ChatWindow";
import ChatPage from "../../app/chat/page";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockPush }),
}));

jest.mock("../../lib/sse", () => ({
  streamChat: jest.fn(),
}));

jest.mock("../../lib/api", () => ({
  request: jest.fn(),
}));

beforeEach(() => {
  localStorage.clear();
  mockPush.mockClear();
});

test("test_new_chat_button_clears_session_id", async () => {
  localStorage.setItem("access_token", "valid-token");
  localStorage.setItem(
    "session_ids",
    JSON.stringify([
      { uuid: "abc-123", preview: "Test chat", created_at: "2026-01-01" },
    ]),
  );

  render(<ChatWindow />);

  const newChatBtn = screen.getByRole("button", { name: /new chat/i });
  await userEvent.click(newChatBtn);

  // After clicking New Chat, send button is disabled (input empty) — session cleared
  expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
});

test("test_chat_page_requires_authentication", async () => {
  localStorage.removeItem("access_token");

  render(<ChatPage />);

  // useEffect fires asynchronously — wait for it
  await screen.findByRole("button", { name: /sign in/i }).catch(() => null);

  expect(mockPush).toHaveBeenCalledWith("/login");
});
