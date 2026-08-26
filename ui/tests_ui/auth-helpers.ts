// Shared test-operator authentication for the Playwright suite.
//
// Real Supabase Auth + RLS is the actual security boundary now (see
// src/routes/_authenticated/route.tsx and supabase/migrations/
// 20260826074136_*.sql) -- anon has no SELECT grant on any reconciliation
// table, so every spec that needs to see real data or an authenticated
// route needs a signed-in operator session, not just the anon key.
//
// Matches ui/.env -- publishable/anon key, same credential the deployed UI
// itself uses. (Playwright does not load .env by default, so this must not
// depend on process.env being populated for the URL/key themselves.)
export const SUPABASE_URL = "https://dtgwbqcjblbcgclogvtv.supabase.co";
export const SUPABASE_ANON_KEY = "sb_publishable_LXQj3IBK6t9AZgn6TQJOmQ_eNqEvfat";

export interface OperatorSession {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  expires_at: number;
  token_type: string;
  user: unknown;
}

/** The localStorage key supabase-js writes the session under -- see
 * src/integrations/supabase/client.ts (default key format: sb-<project-ref>-auth-token). */
export function authStorageKey(): string {
  return `sb-${new URL(SUPABASE_URL).hostname.split(".")[0]}-auth-token`;
}

/**
 * Sign in the dedicated CI/local test operator account via the real
 * Supabase password grant (not a service_role bypass -- this is the same
 * REST endpoint the app's own sign-in form uses).
 *
 * Requires TEST_OPERATOR_EMAIL / TEST_OPERATOR_PASSWORD in the environment
 * -- see ui/README.md "Testing" for how to provision this account (needs an
 * `operator` row in public.user_roles, which only service_role/an existing
 * admin can grant; a fresh self-service signup alone is not enough).
 */
export async function signInTestOperator(): Promise<OperatorSession> {
  const email = process.env["TEST_OPERATOR_EMAIL"];
  const password = process.env["TEST_OPERATOR_PASSWORD"];
  if (!email || !password) {
    throw new Error(
      "TEST_OPERATOR_EMAIL / TEST_OPERATOR_PASSWORD must be set to run the authenticated " +
        "Playwright suite -- see ui/README.md 'Testing' for how to provision a dedicated " +
        "test operator account (needs an `operator` row in public.user_roles).",
    );
  }
  const res = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: SUPABASE_ANON_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    throw new Error(`Test operator sign-in failed: ${res.status} ${await res.text()}`);
  }
  return res.json() as Promise<OperatorSession>;
}

/** Authenticated REST GET against a reconciliation table, using the test
 * operator's real access token (RLS-scoped, same as the app itself uses). */
export async function operatorRestGet<T>(path: string, accessToken: string): Promise<T> {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    headers: { apikey: SUPABASE_ANON_KEY, Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new Error(`Supabase REST fetch failed: ${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}
