import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoginForm from "../../components/LoginForm";
import RegisterForm from "../../components/RegisterForm";

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  jest.resetAllMocks();
});

test("test_login_form_submits_email_and_password", async () => {
  const mockFetch = jest.fn().mockResolvedValue({
    status: 200,
    ok: true,
    json: async () => ({ access_token: "tok", token_type: "bearer" }),
  } as unknown as Response);
  global.fetch = mockFetch;

  const onSuccess = jest.fn();
  render(<LoginForm onSuccess={onSuccess} />);

  await userEvent.type(screen.getByLabelText(/email/i), "user@example.com");
  await userEvent.type(screen.getByLabelText(/password/i), "password123");
  await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

  expect(mockFetch).toHaveBeenCalledTimes(1);
  const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
  const body = JSON.parse(options.body as string) as {
    email: string;
    password: string;
  };
  expect(body.email).toBe("user@example.com");
  expect(body.password).toBe("password123");
});

test("test_register_form_rejects_short_password", async () => {
  const mockFetch = jest.fn();
  global.fetch = mockFetch;

  const onSuccess = jest.fn();
  render(<RegisterForm onSuccess={onSuccess} />);

  await userEvent.type(screen.getByLabelText(/email/i), "user@example.com");
  await userEvent.type(screen.getByLabelText(/password/i), "short");
  await userEvent.click(screen.getByRole("button", { name: /create account/i }));

  expect(mockFetch).not.toHaveBeenCalled();
  expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
});
