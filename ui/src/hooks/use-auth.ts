import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";

import { supabase } from "@/integrations/supabase/client";
import { isBackendConfigured } from "@/lib/backend";

export interface AuthState {
  session: Session | null;
  /** Stable label written into exceptions.assignee. */
  assigneeLabel: string | null;
  loading: boolean;
}

/**
 * Session state for triage. Reads are anon-key only; writes to
 * exceptions.status / assignee / resolution_note require this session.
 */
export function useAuth(): AuthState {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isBackendConfigured()) {
      setLoading(false);
      return;
    }

    let active = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      setSession(data.session ?? null);
      setLoading(false);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next ?? null);
      setLoading(false);
    });

    return () => {
      active = false;
      subscription.subscription.unsubscribe();
    };
  }, []);

  const user = session?.user ?? null;

  return {
    session,
    assigneeLabel: user ? (user.email ?? user.id) : null,
    loading,
  };
}
