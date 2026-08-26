import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests_ui",
  globalSetup: "./tests_ui/global-setup.ts",
  use: {
    baseURL: "http://localhost:8080",
    trace: "on-first-retry",
    // Real Supabase Auth + RLS is the security boundary now -- every spec
    // runs signed in as the dedicated test operator account (seeded by
    // global-setup.ts), matching how a real operator actually reaches any
    // of these routes. See tests_ui/auth-helpers.ts.
    storageState: "tests_ui/.auth/operator.json",
  },
});
