/**
 * Backend availability. The recon engine's data source is the project database,
 * accessed with the anon key under RLS only — there is no service-role usage
 * anywhere in this app.
 *
 * Until the database is enabled and the frozen schema + generated types land,
 * this reports `unconfigured` and every route renders its empty state rather
 * than inventing figures.
 */
export type ConnectionState = "unconfigured" | "connecting" | "online" | "offline";

export function readSupabaseEnv(): { url: string | undefined; anonKey: string | undefined } {
  const env = import.meta.env as Record<string, string | undefined>;
  return {
    url: env["VITE_SUPABASE_URL"],
    anonKey: env["VITE_SUPABASE_PUBLISHABLE_KEY"] ?? env["VITE_SUPABASE_ANON_KEY"],
  };
}

export function isBackendConfigured(): boolean {
  const { url, anonKey } = readSupabaseEnv();
  return Boolean(url && anonKey);
}
