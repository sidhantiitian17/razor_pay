import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const dirname = path.dirname(fileURLToPath(import.meta.url));

import { authStorageKey, signInTestOperator } from "./auth-helpers";

/**
 * Signs in the dedicated test operator account once per suite run and seeds
 * a real browser storageState with the resulting Supabase session, so every
 * spec loads already authenticated -- matching how a real operator uses the
 * app (RLS is the actual gate, not a mocked auth state).
 */
export default async function globalSetup(): Promise<void> {
  const session = await signInTestOperator();

  const browser = await chromium.launch();
  const page = await browser.newPage({ baseURL: "http://localhost:8080" });
  // Any same-origin page works to get a document before writing localStorage.
  await page.goto("/auth");
  await page.evaluate(({ key, value }) => window.localStorage.setItem(key, value), {
    key: authStorageKey(),
    value: JSON.stringify(session),
  });

  const authDir = path.resolve(dirname, ".auth");
  fs.mkdirSync(authDir, { recursive: true });
  await page.context().storageState({ path: path.join(authDir, "operator.json") });

  await browser.close();
}
