# Task: Phase 5A — Frontend MVP

**Phase:** 5A  
**Roadmap goal:** First usable FIFA 2026 web application — auth, chat, and session history.  
**Stable tag at task creation:** `phase-6a-observability-stable`  
**Branch:** `phase-5a-frontend-mvp`  
**Backend test baseline:** 133 tests passing — must remain 133 after this phase  
**Frontend test baseline:** 0 (new)  
**Minimum frontend tests after merge:** 8

---

## Goal

The platform has a complete, production-grade backend but no user interface. All current
interaction requires raw HTTP calls (curl, Swagger UI at `/docs`). This task builds the
first usable web application: a React/Next.js frontend that lets a user register, log in,
send chat messages with streaming AI responses, and navigate between sessions.

The frontend consumes **only existing backend API endpoints**. No new backend routes,
no schema changes, no agent modifications. If a feature cannot be built from the current
API surface, it is deferred or scoped down — the backend is the constraint.

**The goal is "first usable", not "feature complete."** Team browser, prediction tool,
and simulation dashboard are deferred. The chat experience — with auth, streaming, and
session history — is the complete scope.

---

## Scope

**In scope:**
- Bootstrap Next.js 14 (App Router) + TypeScript + Tailwind CSS project in `frontend/`
- Login page (`/login`) — email + password form, JWT stored in `localStorage`
- Register page (`/register`) — email + password form, redirect to login on success
- Chat page (`/chat`) — authenticated, with message input and response display
- Streaming responses — SSE via `fetch` + `ReadableStream` (not `EventSource`, which does
  not support POST or custom headers)
- Session history sidebar — lists sessions stored in `localStorage`; loads message history
  via `GET /api/v1/chat/{uuid}` on selection
- New chat button — clears active session ID so the next POST creates a fresh session
- Auth token persistence — JWT stored in `localStorage`; attached as
  `Authorization: Bearer <token>` on every API call
- Logout — removes token from `localStorage`, redirects to `/login`
- Route guard — unauthenticated users redirected to `/login` for any `/chat` route
- Error handling — form validation errors, 401 unauthorised, network failures all show
  user-facing messages (no silent failures, no raw JSON displayed)
- Mobile-responsive layout — usable on viewport widths from 375px upward
- API client module — centralised `fetch` wrapper in `src/lib/api.ts`
- Add a frontend CI job to `.github/workflows/ci.yml` (`npm ci`, `npm run build`,
  `npm test -- --watchAll=false`)
- Write 8 frontend tests (see Required Tests)
- Update `docs/PROJECT_STATE.md` when implementation is complete

**Out of scope (do not touch):**
- New backend endpoints of any kind
- Backend agent, Redis, LangSmith, RAG, or DB changes
- Team browser, prediction tool, or simulation dashboard
- Admin or user profile management
- Server-side rendering of chat history (client-side fetch is sufficient for MVP)
- WebSocket upgrade from SSE
- `httpOnly` cookie auth (localStorage is acceptable for MVP; noted as TD)
- Docker Compose frontend service (deferred to production hardening phase)

---

## Files Allowed to Change

```
frontend/                          ← everything; currently empty scaffold
.github/workflows/ci.yml           ← add frontend lint + build + test job only
docs/PROJECT_STATE.md
```

All new frontend files live under `frontend/`. No file outside these three targets
may be touched. If a required change falls outside this list, stop and surface it.

---

## Files Not Allowed to Change

```
backend/                           ← all Python source and test files
docs/ARCHITECTURE.md
docs/ROADMAP.md
docs/DECISIONS.md
docs/EXECUTION_WORKFLOW.md
infra/
scripts/
tasks/
```

---

## Acceptance Criteria

Each criterion must be independently verifiable by the QA Agent.

1. `npm run build` exits 0 from `frontend/` with no TypeScript errors.
2. `npm test -- --watchAll=false` exits 0 from `frontend/` with count ≥ 8.
3. `pytest tests/ -q` from `backend/` still exits 0 with count = 133. No backend file
   was modified.
4. `ruff check app tests` from `backend/` exits 0.
5. Unauthenticated `GET /chat` (or any sub-path) redirects to `/login`. Verified by
   the route-guard test and by manual browser check.
6. `POST /api/v1/auth/register` is called with `{email, password}` on register form
   submit. A password shorter than 8 characters is rejected client-side before
   the network call is made.
7. `POST /api/v1/auth/login` returns `{access_token, token_type}` and the token is
   stored in `localStorage` under the key `"access_token"`. Verified by test.
8. `POST /api/v1/chat/stream` is used for all chat submissions. The streaming path
   reads the SSE response with `fetch` + `ReadableStream`, not `EventSource`.
   Text chunks accumulate in the UI as they arrive (not buffered to completion).
9. The `session_uuid` from the SSE final event
   (`{"event":"session","session_uuid":"<uuid>"}`) is stored and passed as
   `session_id` in subsequent requests to the same session.
10. The session history sidebar lists sessions stored in `localStorage`. Selecting a
    session calls `GET /api/v1/chat/{uuid}` and renders its message history.
11. The "New chat" button clears the active `session_id` so the next submission
    creates a fresh session. Verified by test.
12. The logout action removes `"access_token"` from `localStorage` and navigates to
    `/login`. Verified by test.
13. All API calls attach `Authorization: Bearer <token>` from `localStorage`. A 401
    response from any endpoint redirects to `/login` and clears the stored token.
14. The layout is usable at 375px viewport width (no horizontal scroll, no clipped
    inputs). Verified by manual browser check at mobile viewport.
15. Form error states (wrong password, email already registered, network failure)
    display a human-readable message in the UI — not a raw JSON object or stack trace.
16. No `NEXT_PUBLIC_API_URL` or any other secret/credential is hardcoded in source.
    All configurable values read from environment variables via `process.env`.
17. `docs/PROJECT_STATE.md` updated to reflect Phase 5A completion and a new
    "Frontend" section.

---

## Required Tests

Write these 8 tests. Use **Jest + React Testing Library** (`@testing-library/react`).
File locations are prescriptive — use them exactly.

### `frontend/src/__tests__/lib/api.test.ts`

| Function | What it must verify |
|---|---|
| `test_api_client_attaches_bearer_header` | Mock `fetch`; call the API client with a stored token; assert the `Authorization: Bearer <token>` header is present in the captured request. |
| `test_api_client_redirects_on_401` | Mock `fetch` to return `status: 401`; assert that the client clears `localStorage` and calls `router.push("/login")` (or equivalent navigation). |

### `frontend/src/__tests__/lib/auth.test.ts`

| Function | What it must verify |
|---|---|
| `test_token_stored_in_localstorage_after_login` | Mock `fetch` to return `{access_token: "tok", token_type: "bearer"}`; call the login helper; assert `localStorage.getItem("access_token") === "tok"`. |
| `test_logout_removes_token_and_redirects` | Store a token in `localStorage`; call the logout helper; assert `localStorage.getItem("access_token")` is null. |

### `frontend/src/__tests__/components/LoginForm.test.tsx`

| Function | What it must verify |
|---|---|
| `test_login_form_submits_email_and_password` | Render `<LoginForm>`; fill email and password fields; submit; assert `fetch` was called with the correct body. |
| `test_register_form_rejects_short_password` | Render `<RegisterForm>` (or the register page); enter a 7-character password; assert a validation error is shown and `fetch` is NOT called. |

### `frontend/src/__tests__/components/Chat.test.tsx`

| Function | What it must verify |
|---|---|
| `test_new_chat_button_clears_session_id` | Render the chat page with an active session ID in state; click "New chat"; assert the session ID state is cleared (next submit will send `session_id: null`). |
| `test_chat_page_requires_authentication` | Render the chat page component without a token in `localStorage`; assert that `router.push("/login")` is called (or the component renders a redirect). |

**Pattern note:** Use `jest.spyOn(window, "fetch")` or `jest.fn()` to mock network calls.
Use `@testing-library/user-event` for user interactions. Do not use MSW (Mock Service
Worker) unless it is already a project dependency — keep the setup minimal.

The streaming SSE path (`ReadableStream`) does not need a dedicated test at this phase.
The existing backend streaming tests (`test_stream_*` in `test_chat.py`) cover the
server side. A smoke test that the stream endpoint is called is sufficient (covered by
`test_login_form_submits_email_and_password` pattern applied to the chat submit).

---

## Backend API Contract

The frontend must consume only these endpoints. Do not call any other URL paths.

### Auth

| Method | Path | Request body | Success response | Auth required |
|--------|------|-------------|-----------------|---------------|
| POST | `/api/v1/auth/register` | `{email: string, password: string}` | 201 `{id: number, email: string}` | No |
| POST | `/api/v1/auth/login` | `{email: string, password: string}` | 200 `{access_token: string, token_type: "bearer"}` | No |
| GET | `/api/v1/auth/me` | — | 200 `{id: number, email: string}` | Yes |

### Chat

| Method | Path | Request body | Success response | Auth required |
|--------|------|-------------|-----------------|---------------|
| POST | `/api/v1/chat` | `{message: string, session_id?: string}` | 200 `{session_id: string, response: string, agent_trace: array}` | Yes |
| POST | `/api/v1/chat/stream` | `{message: string, session_id?: string}` | SSE stream (see below) | Yes |
| GET | `/api/v1/chat/{uuid}` | — | 200 `{session_uuid: string, messages: [{id, role, content, created_at}]}` | Yes |
| DELETE | `/api/v1/chat/{uuid}` | — | 204 | Yes |

**Auth header:** All authenticated calls require `Authorization: Bearer <token>`.

**Error responses:**
- `401` — invalid/missing token → clear localStorage, redirect to `/login`
- `409` — email already registered (register endpoint)
- `422` — request validation failed (malformed body)

### SSE Stream Format

```
data: [START]

data: <text chunk>

data: <text chunk>

...

data: {"event":"session","session_uuid":"<uuid>"}

data: [DONE]
```

Parsing rules:
- Each line starts with `data: `; strip that prefix.
- `[START]` → discard.
- `[DONE]` → end the stream; stop reading.
- `{"event":"session","session_uuid":"..."}` → parse JSON, store `session_uuid`
  in component state and in `localStorage` under the session list.
- All other strings → append to the displayed response in real time.

`EventSource` does not support POST requests or custom headers. The streaming
implementation **must** use `fetch` with `response.body.getReader()` and a
`TextDecoder` in a `while (true)` read loop.

---

## Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Backend base URL |

Add to `frontend/.env.local.example`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

`NEXT_PUBLIC_` prefix makes the variable available in browser-side code via
`process.env.NEXT_PUBLIC_API_URL`. Do not put secrets in `NEXT_PUBLIC_` variables —
they are bundled into the client JavaScript.

---

## Implementation Notes

### Bootstrap (do this first, in isolation)

From the repo root:
```bash
cd frontend
npx create-next-app@14 . --typescript --tailwind --eslint --app --src-dir --no-import-alias
```

Accept all defaults. Then immediately run `npm run build` — it must exit 0 before any
application code is written. This confirms the scaffold is correct.

Commit the scaffold as a separate sub-step before any feature work.

### Project structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx              ← root layout, font, metadata
│   │   ├── page.tsx                ← redirects to /chat or /login
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   └── chat/page.tsx
│   ├── components/
│   │   ├── LoginForm.tsx
│   │   ├── RegisterForm.tsx
│   │   ├── ChatWindow.tsx          ← message list + input
│   │   ├── MessageBubble.tsx       ← renders one message
│   │   └── SessionSidebar.tsx      ← session list + new chat button
│   ├── lib/
│   │   ├── api.ts                  ← centralised fetch wrapper
│   │   ├── auth.ts                 ← login(), logout(), getToken()
│   │   └── sse.ts                  ← streamChat() using ReadableStream
│   └── __tests__/
│       ├── lib/api.test.ts
│       ├── lib/auth.test.ts
│       └── components/
│           ├── LoginForm.test.tsx
│           └── Chat.test.tsx
├── .env.local.example
├── jest.config.ts
└── jest.setup.ts
```

### API client pattern (`src/lib/api.ts`)

```typescript
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem("access_token");
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers ?? {}),
  };
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem("access_token");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}
```

### SSE streaming pattern (`src/lib/sse.ts`)

```typescript
export async function streamChat(
  message: string,
  sessionId: string | null,
  onChunk: (text: string) => void,
  onSessionId: (uuid: string) => void,
): Promise<void> {
  const token = localStorage.getItem("access_token");
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/chat/stream`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, session_id: sessionId }),
    },
  );
  if (res.status === 401) {
    localStorage.removeItem("access_token");
    window.location.href = "/login";
    return;
  }
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6);
      if (data === "[START]" || data === "[DONE]") continue;
      try {
        const parsed = JSON.parse(data);
        if (parsed.event === "session") onSessionId(parsed.session_uuid);
      } catch {
        onChunk(data);
      }
    }
  }
}
```

### Session history sidebar — localStorage-backed

There is no `GET /api/v1/chat` endpoint that lists all sessions. The sidebar is backed
by `localStorage`:

1. When a new session UUID is received from SSE, append it to
   `localStorage.getItem("session_ids")` (JSON array of `{uuid, created_at, preview}`).
2. On sidebar load, read the array and render one entry per session.
3. On selection, call `GET /api/v1/chat/{uuid}` to load messages.
4. On "New chat", set `activeSessionId` to `null`; the next submit will create a fresh
   session on the backend.

**Implication:** Session history is device-local. If the user logs in from a different
device, they see an empty sidebar. This is an accepted limitation for Phase 5A MVP.
Record as TD-13 in `docs/DECISIONS.md`.

### Route guard pattern

In `src/app/chat/page.tsx`:
```typescript
"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ChatPage() {
  const router = useRouter();
  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.push("/login");
    }
  }, [router]);
  // ...
}
```

Do not use Next.js middleware for the route guard in Phase 5A — it adds complexity
(Edge Runtime, cookies vs localStorage) without benefit for a portfolio deployment.

### Jest configuration

Next.js 14 with App Router requires a custom Jest setup. Use `jest-environment-jsdom`
and `@testing-library/jest-dom` matchers.

`jest.config.ts`:
```typescript
import type { Config } from "jest";
import nextJest from "next/jest.js";
const createJestConfig = nextJest({ dir: "./" });
const config: Config = {
  coverageProvider: "v8",
  testEnvironment: "jsdom",
  setupFilesAfterFramework: ["<rootDir>/jest.setup.ts"],
};
export default createJestConfig(config);
```

`jest.setup.ts`:
```typescript
import "@testing-library/jest-dom";
```

Required dev dependencies:
```bash
npm install -D jest jest-environment-jsdom @testing-library/react \
  @testing-library/jest-dom @testing-library/user-event \
  @types/jest ts-jest
```

### CI workflow addition

Add a second job to `.github/workflows/ci.yml` after `docker-build`, dependent on
`lint-and-test`:

```yaml
  frontend-build-test:
    name: Frontend Build & Test
    runs-on: ubuntu-latest
    needs: lint-and-test
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run build
      - run: npm test -- --watchAll=false --ci
```

This job fails the CI pipeline if the frontend build breaks or any frontend test fails.

### File length constraint

The 500-line limit from `AGENTS.md` applies. Key files expected to approach the limit:
- `src/components/ChatWindow.tsx` — split `MessageBubble.tsx` out early.
- `src/lib/sse.ts` — keep to the stream reader only; no UI logic.

If any file approaches 450 lines during implementation, split it before continuing.

---

## Security Concerns

1. **JWT in `localStorage` is accessible to JavaScript** — XSS on any page can steal
   the token. For Phase 5A MVP this is acceptable. Record as TD-13 in `docs/DECISIONS.md`.
   Production mitigation: `httpOnly` cookie with `SameSite=Strict`.

2. **`NEXT_PUBLIC_API_URL` is public** — it's bundled into the client JS. This is
   intentional (the API URL is not a secret). Never put the `LANGCHAIN_API_KEY` or any
   other backend secret in a `NEXT_PUBLIC_` variable.

3. **Password sent over HTTP in development** — acceptable for local dev. Production
   requires HTTPS; Docker Compose or a reverse proxy handles TLS termination.

4. **No CSRF protection** — JWT-in-header (not cookie) is CSRF-safe by design. This is
   a benefit of the localStorage approach.

---

## Documentation Updates Required

### `docs/PROJECT_STATE.md`

1. Add a new "Frontend" section after "Auth / Security":

```markdown
### Frontend
| Feature | Status |
|---------|--------|
| Login / Register | ✅ Phase 5A |
| Chat with SSE streaming | ✅ Phase 5A |
| Session history sidebar (localStorage) | ✅ Phase 5A |
| Mobile-responsive layout | ✅ Phase 5A |
| Team browser | ❌ Deferred |
| Prediction tool | ❌ Deferred |
| Simulation dashboard | ❌ Deferred |
```

2. Update "Last phase completed" to `Phase 5A` and date.

3. Add tech stack row to the Technology Stack table (in `docs/ARCHITECTURE.md` — note:
   `docs/ARCHITECTURE.md` is a forbidden file for this task; the Release Agent adds it
   post-merge).

### `docs/DECISIONS.md`

Add one entry to the Known Technical Debt Summary:

| TD-13 | JWT stored in `localStorage`; accessible to JS (XSS risk). Session history device-local (no server-side session list endpoint). | Low | Production hardening phase — httpOnly cookies + `GET /api/v1/chat` list endpoint |

Add a decision record:

**Decision: localStorage for JWT and session history**

**Chosen:** Store `access_token` and session UUIDs in `localStorage`. Route guard via
`useEffect` in client components.

**Why:** Simplest approach for a portfolio MVP with no SSR requirement on authenticated
pages. No backend session table changes, no cookie infrastructure, no Next.js middleware.

**Trade-off:** XSS vulnerability on any page exposes the token. Session history is
device-local. Both are accepted limitations documented as TD-13 and deferred to a
production hardening phase.

---

## Rollback Notes

**Stable tag to restore if this branch breaks `main`:** `phase-6a-observability-stable`

```bash
git checkout phase-6a-observability-stable
```

The frontend is entirely new code in `frontend/`. No existing backend file is modified.
A rollback is equivalent to removing the `frontend/` directory and reverting
`.github/workflows/ci.yml`. The backend remains fully functional without the frontend.

The highest-risk step is bootstrapping the Next.js project and configuring Jest for the
App Router — do this first, verify `npm run build` and `npm test` both pass with zero
application code, then proceed feature by feature.
