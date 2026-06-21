import { login, logout } from "../../lib/auth";

beforeEach(() => {
  localStorage.clear();
  Object.defineProperty(window, "location", {
    value: { href: "" },
    writable: true,
  });
});

afterEach(() => {
  jest.resetAllMocks();
});

test("test_token_stored_in_localstorage_after_login", async () => {
  global.fetch = jest.fn().mockResolvedValue({
    status: 200,
    ok: true,
    json: async () => ({ access_token: "tok", token_type: "bearer" }),
  } as unknown as Response);

  await login("user@example.com", "password123");

  expect(localStorage.getItem("access_token")).toBe("tok");
});

test("test_logout_removes_token_and_redirects", () => {
  localStorage.setItem("access_token", "some-token");

  logout();

  expect(localStorage.getItem("access_token")).toBeNull();
  expect(window.location.href).toBe("/login");
});
