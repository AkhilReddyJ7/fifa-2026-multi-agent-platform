import { request } from "../../lib/api";

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  jest.resetAllMocks();
});

test("test_api_client_attaches_bearer_header", async () => {
  localStorage.setItem("access_token", "test-token-123");

  const mockFetch = jest.fn().mockResolvedValue({
    status: 200,
    ok: true,
    json: async () => ({ data: "ok" }),
  } as unknown as Response);
  global.fetch = mockFetch;

  await request("/api/v1/test");

  const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
  const headers = options.headers as Record<string, string>;
  expect(headers["Authorization"]).toBe("Bearer test-token-123");
});

test("test_api_client_redirects_on_401", async () => {
  localStorage.setItem("access_token", "expired-token");

  global.fetch = jest.fn().mockResolvedValue({
    status: 401,
    ok: false,
  } as Response);

  Object.defineProperty(window, "location", {
    value: { href: "" },
    writable: true,
  });

  await expect(request("/api/v1/protected")).rejects.toThrow("Unauthorized");

  expect(localStorage.getItem("access_token")).toBeNull();
  expect(window.location.href).toBe("/login");
});
